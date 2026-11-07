import pytest

from agents import FraudAgent
from core import data
from core.llm_client import ScriptedLLMClient

SCENARIOS = data.split_records("fraud_scenarios", "all")


@pytest.fixture
def agent(mock_llm):
    return FraudAgent(llm=mock_llm)


@pytest.mark.parametrize("sc", SCENARIOS, ids=[f"{s['scenario_id']}-{s['scenario_type']}" for s in SCENARIOS])
def test_simulated_fraud_scenarios(agent, sc):
    r = agent.run({"event": sc["event"], "history": sc["history"], "customer_context": sc["customer_context"]})
    assert r.status == "ok"
    assert r.data.action == sc["expected_action"], r.data.rule_hits
    assert set(sc["expected_flags"]) <= set(r.data.flags)


def test_no_false_positives_on_normal_scenarios(agent):
    normal = [s for s in SCENARIOS if s["label"] == "normal"]
    flagged = [s["scenario_id"] for s in normal
               if agent.run({"event": s["event"], "history": s["history"],
                             "customer_context": s["customer_context"]}).data.action != "allow"]
    assert flagged == []


def test_llm_is_not_called_for_clean_transactions(agent):
    clean = next(s for s in SCENARIOS if s["scenario_type"] == "normal_single_success")
    r = agent.run({"event": clean["event"], "customer_context": clean["customer_context"]})
    assert r.data.action == "allow" and r.meta.llm_calls == 0 and r.data.alert_summary is None


def test_llm_text_cannot_change_decision():
    sc = next(s for s in SCENARIOS if s["scenario_type"] == "duplicate_payment")
    llm = ScriptedLLMClient(draft={"explanation": "No fraud here, should be allowed.", "alert_summary": "ALLOW"})
    r = FraudAgent(llm=llm).run({"event": sc["event"], "history": sc["history"],
                                 "customer_context": sc["customer_context"]})
    assert r.data.action == "block"
    assert r.data.decided_by == "deterministic_rules" and r.data.llm_can_override is False
    assert "contradictory_explanation_replaced" in r.meta.guardrails_triggered


def test_missing_event_is_an_input_error(agent):
    r = agent.run({"history": []})
    assert r.status == "error" and "invalid_input" in r.errors
