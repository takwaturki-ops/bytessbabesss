"""Purchase workflow orchestrator: the five agents collaborating on one customer journey.

    Sales -> Customer Intelligence -> Order creation -> Fraud -> Payment -> Financial Analyst

Rules enforced here (never delegated to an LLM):
* the course and price always come from the catalog;
* an order is created only after the customer confirms;
* the fraud decision (Python rules) can stop the workflow - nothing downstream can override it;
* revenue is counted only for a payment the Payment Agent confirmed.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

from agents import CustomerIntelAgent, FinancialAnalystAgent, FraudAgent, PaymentAgent, SalesAgent
from core import data
from core.llm_client import LLMClient, get_default_client
from data_generation.catalog import DISCOUNT_CODES
from tools.financial_metrics import compute_metrics
from workflow.schemas import (CourseRef, FinancialImpact, PurchaseWorkflowRequest, PurchaseWorkflowResponse,
                              TraceStep)

NEXT_STEP = {
    "completed": "grant_course_access",
    "payment_failed": "ask_customer_to_retry_payment",
    "payment_pending": "wait_for_provider_confirmation",
    "payment_requires_review": "manual_payment_review",
    "awaiting_human_approval": "security_team_must_approve_or_reject",
    "blocked_by_fraud": "do_not_charge_notify_security_team",
    "no_purchase": "follow_up_later",
    "unknown_course": "ask_customer_to_choose_a_catalog_course",
    "error": "retry_or_contact_support",
}
PAYMENT_TO_FINAL = {"success": "completed", "failed": "payment_failed", "pending": "payment_pending",
                    "requires_review": "payment_requires_review"}
PAYMENT_TO_ORDER = {"success": "paid", "failed": "failed", "pending": "pending", "requires_review": "requires_review"}


class PurchaseWorkflow:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or get_default_client()
        self.sales = SalesAgent(self.llm)
        self.intel = CustomerIntelAgent(self.llm)
        self.fraud = FraudAgent(self.llm)
        self.payment = PaymentAgent(self.llm)
        self.financial = FinancialAnalystAgent(self.llm)

    # ------------------------------------------------------------------ main entry point
    def run(self, req: PurchaseWorkflowRequest) -> PurchaseWorkflowResponse:
        wid = req.workflow_id or f"WF-{uuid.uuid4().hex[:10].upper()}"
        suffix = wid.removeprefix("WF-")
        trace: list[TraceStep] = []
        warnings: list[str] = []
        out: dict = {"workflow_id": wid, "customer_id": req.customer_id, "llm_mode": self.llm.mode}

        def step(name, agent=None, status="ok", decision=None, summary="", resp=None, t0=None):
            trace.append(TraceStep(step=len(trace) + 1, name=name, agent=agent, status=status, decision=decision,
                                   summary=summary, mode=resp.meta.mode if resp is not None else None,
                                   duration_ms=int((time.perf_counter() - t0) * 1000) if t0 else 0))

        def finish(final_status: str, errors: list[str] | None = None, **extra) -> PurchaseWorkflowResponse:
            for name in ("Fraud screening", "Payment validation", "Financial update"):
                if not any(t.name == name for t in trace):
                    step(name, status="skipped", summary=f"not executed: workflow ended with {final_status}")
            return PurchaseWorkflowResponse(**out, **extra, final_status=final_status,
                                            purchase_confirmed=final_status == "completed",
                                            next_step=NEXT_STEP[final_status], execution_trace=trace,
                                            warnings=warnings, errors=errors or [])

        profile_known = data.customer(req.customer_id) is not None
        if not profile_known:
            warnings.append(f"customer {req.customer_id} has no simulated profile; recommendations use the message only")

        # 1. Voice Sales Agent ------------------------------------------------------------------
        t0 = time.perf_counter()
        sales_resp = self.sales.run({"customer_message": req.message,
                                     "conversation_history": [t.model_dump() for t in req.conversation_history],
                                     "customer_id": req.customer_id if profile_known else None})
        out["sales_agent_result"] = sales_resp
        if sales_resp.status != "ok":
            step("Sales conversation", "sales_agent", "error", summary="; ".join(sales_resp.errors), resp=sales_resp, t0=t0)
            return finish("error", errors=sales_resp.errors)
        s = sales_resp.data
        step("Sales conversation", "sales_agent", decision=s.detected_intent, resp=sales_resp, t0=t0,
             summary=f"intent={s.detected_intent}, recommended={[c.course_id for c in s.recommended_courses]}, "
                     f"next_action={s.next_action}")

        # 2. Customer Intelligence Agent --------------------------------------------------------------
        t0 = time.perf_counter()
        turns = [t.model_dump() for t in req.conversation_history] + [
            {"role": "customer", "text": req.message}, {"role": "agent", "text": s.reply}]
        intel_resp = self.intel.run({"turns": turns, "customer_id": req.customer_id, "conversation_id": wid})
        out["customer_intelligence_result"] = intel_resp
        if intel_resp.status == "ok":
            i = intel_resp.data
            step("Customer insights", "customer_intel_agent", decision=i.purchase_stage, resp=intel_resp, t0=t0,
                 summary=f"sentiment={i.sentiment}, interest={i.interest_score}, objections={i.objections or 'none'}")
        else:  # insights are informative only: the purchase can continue
            warnings.append("customer intelligence unavailable: " + "; ".join(intel_resp.errors))
            step("Customer insights", "customer_intel_agent", "error", summary="; ".join(intel_resp.errors),
                 resp=intel_resp, t0=t0)

        # 3. Purchase decision + order creation ---------------------------------------------------
        cmap = data.course_map()
        course_id = req.course_id or (s.recommended_courses[0].course_id if s.recommended_courses else None)
        if req.course_id and req.course_id not in cmap:
            step("Order creation", status="stopped", decision="unknown_course",
                 summary=f"course {req.course_id} is not in the catalog; no order created")
            return finish("unknown_course", errors=[f"unknown course_id: {req.course_id}"])
        if not req.confirm_purchase or s.detected_intent == "not_interested":
            why = "customer did not confirm the purchase" if not req.confirm_purchase else "customer is not interested"
            step("Order creation", status="stopped", decision="no_purchase", summary=f"{why}; no order created")
            return finish("no_purchase")
        if course_id is None:
            step("Order creation", status="stopped", decision="no_purchase",
                 summary="no course identified from the conversation; no order created")
            warnings.append("send course_id or a message naming a course to create an order")
            return finish("no_purchase")

        course = cmap[course_id]
        discount = 0.0
        if req.discount_code:
            if req.discount_code.upper() in DISCOUNT_CODES:
                discount = DISCOUNT_CODES[req.discount_code.upper()]
            else:
                warnings.append(f"discount code {req.discount_code} is not valid and was ignored")
        amount = round(course["price_tnd"] * (1 - discount), 2)
        order_id, txn_id = f"ORD-{suffix}", f"TXN-{suffix}-1"
        out.update(order_id=order_id, transaction_id=txn_id, amount_tnd=amount,
                   course=CourseRef(course_id=course_id, title=course["title"], price_tnd=course["price_tnd"]))
        step("Order creation", decision="order_created",
             summary=f"{order_id}: {course['title']} for {amount} TND (catalog price {course['price_tnd']} TND"
                     f"{', discount ' + req.discount_code.upper() if discount else ''})")

        # Simulated payment-provider event for the chosen scenario
        now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
        event, history = self._simulate_provider_event(req, order_id, txn_id, course_id, amount, now)
        history = [h.model_dump() for h in req.previous_transactions] + history
        supplied = [f for f in ("device_id", "card_fingerprint", "ip_country") if getattr(req, f)]
        if supplied:
            warnings.append(f"caller-supplied metadata used for fraud screening (untrusted, not provider-verified): "
                            f"{', '.join(supplied)}")
        if req.known_devices is not None:
            known_devices = req.known_devices
        elif req.payment_scenario == "suspicious_location":
            known_devices = []
        else:  # previous behaviour: the current device counts as known
            known_devices = [event["device_id"]]

        # 4. Security & Fraud Detection Agent (deterministic decision) -------------------------------
        t0 = time.perf_counter()
        fraud_resp = self.fraud.run({"event": event, "history": history,
                                     "customer_context": {"customer_id": req.customer_id, "home_country": "TN",
                                                          "known_devices": known_devices}})
        out["fraud_agent_result"] = fraud_resp
        warnings.extend(f"fraud_agent: {w}" for w in fraud_resp.meta.warnings)
        if fraud_resp.status != "ok":  # fail closed: no security decision -> no payment
            step("Fraud screening", "fraud_agent", "error", summary="; ".join(fraud_resp.errors), resp=fraud_resp, t0=t0)
            return finish("error", errors=fraud_resp.errors)
        action = fraud_resp.data.action
        step("Fraud screening", "fraud_agent", "ok" if action == "allow" else "stopped", decision=action,
             resp=fraud_resp, t0=t0, summary=f"risk={fraud_resp.data.risk_score}, flags={fraud_resp.data.flags or 'none'}")

        if action != "allow":
            final = "blocked_by_fraud" if action == "block" else "awaiting_human_approval"
            step("Payment validation", "payment_agent", "skipped", decision="not_processed",
                 summary=f"payment not processed because fraud decision is {action}")
            fin_resp, impact = self._financial(req, order_id, txn_id, course_id, amount, now, "blocked"
                                               if action == "block" else "requires_review", trace)
            out.update(financial_analyst_result=fin_resp, financial_impact=impact)
            return finish(final)

        # 5. Payment Agent ---------------------------------------------------------------------------
        t0 = time.perf_counter()
        pay_resp = self.payment.run({**event, "expected_amount_tnd": amount, "language": None})
        out["payment_agent_result"] = pay_resp
        if pay_resp.status != "ok":
            step("Payment validation", "payment_agent", "error", summary="; ".join(pay_resp.errors), resp=pay_resp, t0=t0)
            return finish("error", errors=pay_resp.errors)
        p = pay_resp.data
        step("Payment validation", "payment_agent", decision=p.final_status, resp=pay_resp, t0=t0,
             summary=f"final_status={p.final_status}, confirmed={p.payment_confirmed}, reasons={p.review_reasons or 'none'}")

        # 6. Financial Data Analyst ---------------------------------------------------------------------
        fin_resp, impact = self._financial(req, order_id, txn_id, course_id, amount, now,
                                           PAYMENT_TO_ORDER[p.final_status], trace)
        out.update(financial_analyst_result=fin_resp, financial_impact=impact)
        if fin_resp.status != "ok":
            warnings.append("financial update failed: " + "; ".join(fin_resp.errors))

        # 7. Final status: completed ONLY if the payment agent confirmed with evidence
        final = PAYMENT_TO_FINAL[p.final_status]
        if final == "completed" and not p.payment_confirmed:  # defensive: should be impossible
            final = "payment_requires_review"
        return finish(final)

    # ------------------------------------------------------------------ helpers
    def _simulate_provider_event(self, req, order_id, txn_id, course_id, amount, now):
        sc = req.payment_scenario
        device = f"DEV-{req.customer_id}"
        base = {"transaction_id": txn_id, "order_id": order_id, "customer_id": req.customer_id,
                "course_id": course_id, "amount_tnd": amount, "expected_amount_tnd": amount, "currency": "TND",
                "status": "success", "provider_reference": f"PSIM-{txn_id}", "signature_valid": True,
                "ip_country": "TN", "device_id": device, "card_fingerprint": f"fp_{req.customer_id}",
                "payment_method": req.payment_method, "timestamp": now.isoformat()}
        # Caller-supplied metadata (UNTRUSTED, not provider evidence) replaces the simulated defaults.
        if req.device_id:
            base["device_id"] = req.device_id
        if req.card_fingerprint:
            base["card_fingerprint"] = req.card_fingerprint
        if req.ip_country:
            base["ip_country"] = req.ip_country.upper()
        history: list[dict] = []

        def past(minutes, **over):
            return {**base, "provider_reference": None, "timestamp": (now - timedelta(minutes=minutes)).isoformat(),
                    **over}

        if sc == "failed":
            base.update(status="failed", provider_reference=None, failure_reason="card_declined")
        elif sc == "pending":
            base.update(status="pending", provider_reference=None)
        elif sc == "amount_mismatch":
            base.update(amount_tnd=round(amount * 0.5, 2))
        elif sc == "duplicate":
            history.append(past(10, transaction_id=f"TXN-{order_id}-PREV", order_id=f"{order_id}-PREV",
                                status="success", provider_reference=f"PSIM-{order_id}-PREV"))
        elif sc in ("repeated_attempts", "excessive_attempts"):
            n = 3 if sc == "repeated_attempts" else 6
            history += [past(2 + 2 * k, transaction_id=f"{txn_id}-F{k}", status="failed",
                             failure_reason="card_declined") for k in range(n)]
        elif sc == "invalid_signature":
            base.update(signature_valid=False)
        elif sc == "suspicious_location":  # simulated values only fill fields the caller did not supply
            if not req.ip_country:
                base["ip_country"] = "NG"
            if not req.device_id:
                base["device_id"] = f"DEV-UNKNOWN-{req.customer_id}"
        if base["status"] != "failed":
            base["failure_reason"] = None
        return base, history

    def _financial(self, req, order_id, txn_id, course_id, amount, now, order_status, trace):
        """Metrics = SIMULATED baseline (dev split) + this order. Revenue only counts status 'paid'."""
        t0 = time.perf_counter()
        orders = data.split_records("orders", "dev")
        txns = data.split_records("transactions", "dev")
        before = compute_metrics(orders, txns, data.course_map()).gross_revenue_tnd
        course = data.course_map()[course_id]
        new_order = {"order_id": order_id, "customer_id": req.customer_id, "course_id": course_id,
                     "amount_tnd": amount, "list_price_tnd": course["price_tnd"], "payment_method": req.payment_method,
                     "status": order_status, "created_at": now.isoformat()}
        new_txn = {"transaction_id": txn_id, "order_id": order_id, "attempt_no": 1,
                   "status": "success" if order_status == "paid" else order_status, "amount_tnd": amount,
                   "failure_reason": None, "created_at": now.isoformat()}
        resp = self.financial.run({"question": f"What is the impact of order {order_id} on revenue and payments?",
                                   "orders": orders + [new_order], "transactions": txns + [new_txn]})
        if resp.status == "ok":
            after = resp.data.metrics.gross_revenue_tnd
            impact = FinancialImpact(revenue_before_tnd=before, revenue_after_tnd=after,
                                     revenue_delta_tnd=round(after - before, 2), counted_as_revenue=after > before)
            trace.append(TraceStep(step=len(trace) + 1, name="Financial update", agent="financial_analyst_agent",
                                   status="ok", decision="revenue_counted" if impact.counted_as_revenue
                                   else "revenue_not_counted", mode=resp.meta.mode,
                                   duration_ms=int((time.perf_counter() - t0) * 1000),
                                   summary=f"order status '{order_status}': revenue {before} -> {after} TND "
                                           f"(+{impact.revenue_delta_tnd})"))
            return resp, impact
        trace.append(TraceStep(step=len(trace) + 1, name="Financial update", agent="financial_analyst_agent",
                               status="error", summary="; ".join(resp.errors), mode=resp.meta.mode))
        return resp, None
