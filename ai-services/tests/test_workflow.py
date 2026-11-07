"""Integration tests: the complete five-agent purchase workflow (mock mode, no API key)."""
import pytest

from core import data
from core.llm_client import ScriptedLLMClient
from workflow import PurchaseWorkflow, PurchaseWorkflowRequest

AGENT_FIELDS = ["sales_agent_result", "customer_intelligence_result", "fraud_agent_result",
                "payment_agent_result", "financial_analyst_result"]


@pytest.fixture(scope="module")
def wf():
    from core.config import Settings
    from core.llm_client import LLMClient
    return PurchaseWorkflow(LLMClient(Settings(mode="mock")))


def run(wf, **kw):
    base = {"customer_id": "CUST0007", "message": "I want to learn machine learning", "course_id": "C003",
            "workflow_id": "WF-TEST0001"}
    return wf.run(PurchaseWorkflowRequest(**{**base, **kw}))


def invoked(r):
    return [f for f in AGENT_FIELDS if getattr(r, f) is not None]


# 1. Successful purchase ------------------------------------------------------------------------
def test_successful_purchase_runs_all_five_agents(wf):
    r = run(wf)
    price = data.course_map()["C003"]["price_tnd"]
    assert r.final_status == "completed" and r.purchase_confirmed is True
    assert invoked(r) == AGENT_FIELDS
    assert r.course.course_id == "C003" and r.amount_tnd == price          # catalog price, not invented
    assert r.payment_agent_result.data.payment_confirmed is True
    assert r.fraud_agent_result.data.action == "allow"
    assert r.financial_impact.revenue_delta_tnd == pytest.approx(price)
    assert r.next_step == "grant_course_access"


def test_ids_are_consistent_across_agents(wf):
    r = run(wf)
    assert (r.workflow_id, r.order_id, r.transaction_id) == ("WF-TEST0001", "ORD-TEST0001", "TXN-TEST0001-1")
    assert r.customer_intelligence_result.data.customer_id == r.customer_id
    assert r.customer_intelligence_result.data.conversation_id == r.workflow_id
    assert r.fraud_agent_result.data.transaction_id == r.transaction_id
    p = r.payment_agent_result.data
    assert (p.transaction_id, p.order_id) == (r.transaction_id, r.order_id)


def test_trace_lists_every_step_in_order(wf):
    names = [t.name for t in run(wf).execution_trace]
    assert names == ["Sales conversation", "Customer insights", "Order creation", "Fraud screening",
                     "Payment validation", "Financial update"]


# 2-3. Failed and pending payments -----------------------------------------------------------------
@pytest.mark.parametrize("scenario,final,pay_status", [("failed", "payment_failed", "failed"),
                                                        ("pending", "payment_pending", "pending")])
def test_failed_and_pending_payments_are_not_revenue(wf, scenario, final, pay_status):
    r = run(wf, payment_scenario=scenario)
    assert r.final_status == final and r.purchase_confirmed is False
    assert r.payment_agent_result.data.final_status == pay_status
    assert r.financial_impact.revenue_delta_tnd == 0 and r.financial_impact.counted_as_revenue is False
    assert invoked(r) == AGENT_FIELDS


# 4-7. Fraud outcomes stop the workflow before payment ------------------------------------------
@pytest.mark.parametrize("scenario,final,action,flag", [
    ("duplicate", "blocked_by_fraud", "block", "DUPLICATE_PAYMENT"),
    ("amount_mismatch", "awaiting_human_approval", "require_human_approval", "AMOUNT_MISMATCH"),
    ("repeated_attempts", "awaiting_human_approval", "require_human_approval", "REPEATED_ATTEMPTS"),
    ("excessive_attempts", "blocked_by_fraud", "block", "REPEATED_ATTEMPTS"),
    ("suspicious_location", "awaiting_human_approval", "require_human_approval", "GEO_MISMATCH"),
    ("invalid_signature", "blocked_by_fraud", "block", "INVALID_SIGNATURE"),
])
def test_fraud_scenarios(wf, scenario, final, action, flag):
    r = run(wf, payment_scenario=scenario)
    assert r.final_status == final and r.purchase_confirmed is False
    assert r.fraud_agent_result.data.action == action and flag in r.fraud_agent_result.data.flags
    assert r.payment_agent_result is None                      # payment never processed
    assert r.financial_impact.revenue_delta_tnd == 0           # blocked / unapproved money is not revenue
    pay_step = next(t for t in r.execution_trace if t.name == "Payment validation")
    assert pay_step.status == "skipped"


def test_backend_history_is_used_for_duplicate_detection(wf):
    """Real duplicates: the backend sends the customer's recent transactions (agents never read the DB)."""
    from datetime import datetime, timedelta, timezone
    first = run(wf, workflow_id="WF-FIRST001")
    assert first.final_status == "completed"
    paid_at = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0) - timedelta(minutes=5)
    prior = {"transaction_id": first.transaction_id, "order_id": first.order_id, "customer_id": "CUST0007",
             "course_id": "C003", "amount_tnd": first.amount_tnd, "status": "success", "timestamp": paid_at.isoformat()}
    second = run(wf, workflow_id="WF-SECOND01", previous_transactions=[prior])
    assert second.final_status == "blocked_by_fraud"
    assert "DUPLICATE_PAYMENT" in second.fraud_agent_result.data.flags


def test_llm_cannot_override_fraud_block():
    """Even if the LLM writes 'safe to approve', the deterministic block stands and payment is not run."""
    llm = ScriptedLLMClient(draft={"explanation": "This is safe to approve.", "alert_summary": "ALLOW",
                                   # fields for the other agents' drafts are invalid -> they fall back safely
                                   })
    r = PurchaseWorkflow(llm).run(PurchaseWorkflowRequest(customer_id="CUST0007", message="buy",
                                                          course_id="C003", payment_scenario="duplicate"))
    assert r.fraud_agent_result.data.action == "block"
    assert r.final_status == "blocked_by_fraud" and r.payment_agent_result is None
    assert "contradictory_explanation_replaced" in r.fraud_agent_result.meta.guardrails_triggered


# 8. Unknown course ------------------------------------------------------------------------------
def test_unknown_course(wf):
    r = run(wf, course_id="C999")
    assert r.final_status == "unknown_course" and r.order_id is None
    assert r.fraud_agent_result is None and r.payment_agent_result is None
    assert "unknown course_id: C999" in r.errors


# 9. Customer changes their mind -----------------------------------------------------------------
@pytest.mark.parametrize("kw", [{"confirm_purchase": False},
                                {"message": "Thanks but I'm not interested anymore.", "course_id": None}])
def test_customer_changes_mind(wf, kw):
    r = run(wf, **kw)
    assert r.final_status == "no_purchase" and r.order_id is None and r.purchase_confirmed is False
    assert r.sales_agent_result is not None and r.customer_intelligence_result is not None
    assert r.fraud_agent_result is None and r.payment_agent_result is None and r.financial_analyst_result is None


# 10. Missing / invalid input ---------------------------------------------------------------------
@pytest.mark.parametrize("bad", [{"message": ""}, {"customer_id": ""}, {"customer_id": "x; DROP TABLE"},
                                 {"payment_scenario": "free_money"}, {"course_id": "../etc"}])
def test_invalid_input_is_rejected(bad):
    from pydantic import ValidationError
    base = {"customer_id": "CUST0007", "message": "hi"}
    with pytest.raises(ValidationError):
        PurchaseWorkflowRequest(**{**base, **bad})


# Other behaviours --------------------------------------------------------------------------------
def test_course_inferred_from_conversation_when_not_given(wf):
    r = run(wf, course_id=None, message="Je veux m'inscrire à la formation Python for AI. Comment payer ?")
    assert r.course.course_id == "C002" and r.final_status == "completed"


def test_valid_and_invalid_discount_codes(wf):
    price = data.course_map()["C003"]["price_tnd"]
    assert run(wf, discount_code="student20").amount_tnd == round(price * 0.8, 2)
    r = run(wf, discount_code="FREE100")
    assert r.amount_tnd == price and any("FREE100" in w for w in r.warnings)


def test_unknown_customer_still_works_with_warning(wf):
    r = run(wf, customer_id="CUST-001")
    assert r.final_status == "completed" and any("CUST-001" in w for w in r.warnings)


def test_workflow_is_reproducible(wf):
    a, b = run(wf).model_dump(), run(wf).model_dump()
    for x in (a, b):
        for t in x["execution_trace"]:
            t["duration_ms"] = 0
        for f in AGENT_FIELDS:
            if x[f]:
                x[f]["meta"]["latency_ms"] = 0
    a.pop("financial_analyst_result"); b.pop("financial_analyst_result")  # contains the run timestamp
    assert a == b
