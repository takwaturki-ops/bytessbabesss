"""Jury demo: one customer journey through all five agents, then the same purchase under each risk scenario.

Run from ai-services/:   .venv\\Scripts\\python.exe main.py workflow-demo
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm_client import get_default_client  # noqa: E402
from workflow import PurchaseWorkflow, PurchaseWorkflowRequest  # noqa: E402


def main() -> None:
    wf = PurchaseWorkflow(get_default_client())
    print("9antra purchase workflow demo - SIMULATED data and payments")
    print(f"LLM mode: {wf.llm.mode}\n")

    req = PurchaseWorkflowRequest(customer_id="CUST0007", message="I want to learn machine learning",
                                  course_id="C003", payment_scenario="success", workflow_id="WF-DEMO0001")
    r = wf.run(req)
    print(f"Customer {r.customer_id}: {req.message!r}")
    print(f"Sales reply: {r.sales_agent_result.data.reply}")
    i = r.customer_intelligence_result.data
    print(f"Insights: intent={i.primary_intent}, sentiment={i.sentiment}, interest={i.interest_score}/100")
    print(f"Order {r.order_id} / transaction {r.transaction_id}: {r.course.title} = {r.amount_tnd} TND")
    print(f"Fraud: {r.fraud_agent_result.data.action} (risk {r.fraud_agent_result.data.risk_score})")
    p = r.payment_agent_result.data
    print(f"Payment: {p.final_status}, confirmed={p.payment_confirmed} -> {p.customer_message}")
    fi = r.financial_impact
    print(f"Revenue: {fi.revenue_before_tnd} -> {fi.revenue_after_tnd} TND (+{fi.revenue_delta_tnd})")
    print(f"FINAL: {r.final_status} | next step: {r.next_step}\n")

    print("Execution trace:")
    for t in r.execution_trace:
        print(f"  {t.step}. {t.name:20s} [{t.status:7s}] {t.decision}")

    print("\nSame purchase, different simulated payment outcomes:")
    print(f"  {'scenario':20s} {'fraud':24s} {'payment':16s} {'final status':25s} revenue +")
    for sc in ["success", "failed", "pending", "amount_mismatch", "duplicate", "repeated_attempts",
               "excessive_attempts", "invalid_signature", "suspicious_location"]:
        r = wf.run(req.model_copy(update={"payment_scenario": sc, "workflow_id": None}))
        pay = r.payment_agent_result.data.final_status if r.payment_agent_result else "not processed"
        print(f"  {sc:20s} {r.fraud_agent_result.data.action:24s} {pay:16s} {r.final_status:25s} "
              f"{r.financial_impact.revenue_delta_tnd}")
    r = wf.run(req.model_copy(update={"confirm_purchase": False, "workflow_id": None}))
    print(f"  {'customer declines':20s} {'-':24s} {'-':16s} {r.final_status:25s} -")


if __name__ == "__main__":
    main()
