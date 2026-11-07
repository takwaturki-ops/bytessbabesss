import pytest

from agents import PaymentAgent
from core import data
from core.llm_client import ScriptedLLMClient

BASE = {"transaction_id": "T1", "order_id": "O1", "status": "success", "amount_tnd": 149.0,
        "expected_amount_tnd": 149.0, "currency": "TND", "provider_reference": "PSIM-1", "signature_valid": True}


@pytest.fixture
def agent(mock_llm):
    return PaymentAgent(llm=mock_llm)


def test_confirmed_success(agent):
    r = agent.run(BASE)
    assert r.status == "ok" and r.data.final_status == "success" and r.data.payment_confirmed


@pytest.mark.parametrize("override,reason", [
    ({"provider_reference": None}, "missing_provider_reference"),
    ({"signature_valid": False}, "signature_invalid_or_missing"),
    ({"signature_valid": None}, "signature_invalid_or_missing"),
    ({"amount_tnd": 140.0}, "amount_mismatch"),
    ({"currency": "USD"}, "currency_not_tnd"),
])
def test_success_without_full_evidence_is_never_confirmed(agent, override, reason):
    r = agent.run({**BASE, **override})
    assert r.data.final_status == "requires_review"
    assert r.data.payment_confirmed is False
    assert reason in r.data.review_reasons


@pytest.mark.parametrize("raw,expected", [("failed", "failed"), ("declined", "failed"), ("pending", "pending"),
                                          ("processing", "pending"), ("requires_review", "requires_review"),
                                          ("???", "requires_review")])
def test_status_normalisation(agent, raw, expected):
    assert agent.run({**BASE, "status": raw}).data.final_status == expected


def test_llm_cannot_claim_success(agent):
    llm = ScriptedLLMClient(draft={"summary": "Paiement réussi.", "customer_message": "Payment successful!"})
    r = PaymentAgent(llm=llm).run({**BASE, "status": "failed"})
    assert r.data.final_status == "failed"
    assert "unverified_success_claim_removed" in r.meta.guardrails_triggered
    assert "successful" not in r.data.customer_message.lower()


def test_explain_false_skips_llm(agent):
    r = agent.run({**BASE, "explain": False})
    assert r.meta.llm_calls == 0 and not r.data.summary.startswith("[MOCK]")


def test_no_unsafe_confirmation_on_simulated_transactions(agent):
    for t in data.split_records("transactions", "all"):
        r = agent.run({**t, "explain": False}).data
        assert r.final_status == t["status"]
        assert r.payment_confirmed == (t["status"] == "success")
