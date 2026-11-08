"""Regression tests: transactions whose order_id matches no supplied order are excluded (unchanged behaviour)
and now reported in meta.warnings. Metrics must be identical with or without the warning."""
import pytest
from fastapi.testclient import TestClient

from agents import FinancialAnalystAgent
from api.main import app
from core.config import Settings
from core.llm_client import LLMClient
from tools.financial_metrics import unmatched_transactions

PREFIX = "transactions_excluded_unmatched_order:"


def order(oid, amt, status, created="2026-11-08T10:00:00"):
    return {"order_id": oid, "course_id": "C003", "amount_tnd": amt, "list_price_tnd": amt, "payment_method": "card",
            "status": status, "created_at": created}


def txn(tid, oid, status, amt):
    return {"transaction_id": tid, "order_id": oid, "attempt_no": 1, "status": status, "amount_tnd": amt,
            "failure_reason": "card_declined" if status == "failed" else None, "created_at": "2026-11-08T10:00:00"}


ORDERS = [order("ORD-FIN-001", 349.0, "paid"), order("ORD-FIN-002", 299.0, "paid"), order("ORD-FIN-003", 199.0, "failed")]
VALID_TXNS = [txn("TX-FIN-001", "ORD-FIN-001", "success", 349.0), txn("TX-FIN-002", "ORD-FIN-002", "success", 299.0),
              txn("TX-FIN-003", "ORD-FIN-003", "failed", 199.0)]


@pytest.fixture(scope="module")
def agent():
    return FinancialAnalystAgent(LLMClient(Settings(mode="mock")))


def run(agent, orders, txns, **kw):
    r = agent.run({"question": "test", "orders": orders, "transactions": txns, **kw})
    assert r.status == "ok"
    return r


def unmatched(r):
    return [w for w in r.meta.warnings if w.startswith(PREFIX)]


def test_transaction_referencing_missing_order(agent):
    r = run(agent, ORDERS, VALID_TXNS + [txn("TX-FIN-004", "ORD-FIN-004", "pending", 150.0)])
    w = unmatched(r)
    assert len(w) == 1
    assert w[0].startswith(PREFIX + "1 ")
    assert "TX-FIN-004" in w[0] and "ORD-FIN-004" in w[0]
    # existing filtering behaviour is unchanged: still excluded from every count
    assert r.data.data_scope.n_transactions == 3 and r.data.metrics.pending_transactions == 0


def test_transaction_referencing_valid_order(agent):
    r = run(agent, ORDERS, VALID_TXNS)
    assert unmatched(r) == []
    assert r.data.data_scope.n_transactions == 3


def test_mixture_of_valid_and_invalid_references(agent):
    txns = VALID_TXNS + [txn("TX-BAD-1", "ORD-MISSING-A", "pending", 150.0),
                         txn("TX-BAD-2", "ORD-MISSING-A", "failed", 150.0),
                         txn("TX-BAD-3", "ord-fin-001", "requires_review", 349.0),   # case differs -> no match
                         txn("TX-OK-4", "ORD-FIN-003", "pending", 199.0)]
    r = run(agent, ORDERS, txns)
    w = unmatched(r)
    assert len(w) == 1 and w[0].startswith(PREFIX + "3 ")
    for tid in ("TX-BAD-1", "TX-BAD-2", "TX-BAD-3"):
        assert tid in w[0]
    assert "TX-OK-4" not in w[0] and "TX-FIN-001" not in w[0]
    assert "ORD-MISSING-A" in w[0] and "ord-fin-001" in w[0]
    assert w[0].count("ORD-MISSING-A") == 1                       # unmatched order ids are de-duplicated
    assert r.data.data_scope.n_transactions == 4                  # 3 valid + TX-OK-4


def test_metrics_identical_with_or_without_orphans(agent):
    clean = run(agent, ORDERS, VALID_TXNS, explain=False)
    noisy = run(agent, ORDERS, VALID_TXNS + [txn("TX-X", "ORD-NOPE", "success", 999.0)], explain=False)
    assert clean.data.metrics == noisy.data.metrics               # revenue and payment metrics untouched
    assert clean.data.narrative == noisy.data.narrative


def test_date_filter_exclusions_are_not_reported_as_unmatched(agent):
    orders = ORDERS + [order("ORD-OLD", 100.0, "paid", created="2026-01-01T10:00:00")]
    txns = VALID_TXNS + [txn("TX-OLD", "ORD-OLD", "success", 100.0)]
    r = run(agent, orders, txns, date_from="2026-11-01", date_to="2026-11-30")
    assert unmatched(r) == []                                     # its order WAS supplied, only filtered by date


def test_simulated_dataset_produces_no_unmatched_warning(agent):
    for split in ("dev", "eval", "all"):
        r = agent.run({"split": split, "explain": False})
        assert unmatched(r) == []


def test_helper_handles_missing_keys():
    tx_ids, order_ids = unmatched_transactions([{"order_id": "A"}], [{"transaction_id": "T1"},
                                                                     {"transaction_id": "T2", "order_id": "A"}])
    assert tx_ids == ["T1"] and order_ids == ["None"]


def test_api_returns_200_with_warning_and_same_shape():
    client = TestClient(app)
    body = {"question": "test", "orders": ORDERS, "transactions": VALID_TXNS + [txn("TX-FIN-004", "ORD-FIN-004",
                                                                                        "pending", 150.0)]}
    r = client.post("/agents/financial", json=body)
    assert r.status_code == 200
    j = r.json()
    assert set(j) == {"agent", "status", "data", "errors", "meta"}      # envelope unchanged
    assert any(w.startswith(PREFIX) and "TX-FIN-004" in w for w in j["meta"]["warnings"])
    assert j["data"]["data_scope"]["n_transactions"] == 3
