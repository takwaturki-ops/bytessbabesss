"""HTTP tests for the FastAPI service (in-process TestClient, mock mode)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
OK_BODY = {"customer_id": "CUST0007", "message": "I want to learn machine learning", "course_id": "C003",
           "payment_scenario": "success"}


def test_health_reports_mode():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["mode"] == "mock" and body["data"] == "simulated"
    assert len(body["agents"]) == 5


def test_swagger_docs_available():
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/workflow/purchase" in spec["paths"]


def test_purchase_success_returns_full_structure():
    r = client.post("/workflow/purchase", json=OK_BODY)
    assert r.status_code == 200
    b = r.json()
    for key in ["workflow_id", "customer_id", "order_id", "transaction_id", "sales_agent_result",
                "customer_intelligence_result", "fraud_agent_result", "payment_agent_result",
                "financial_analyst_result", "final_status", "execution_trace", "warnings", "errors"]:
        assert key in b, key
    assert b["final_status"] == "completed" and b["purchase_confirmed"] is True
    assert b["order_id"].startswith("ORD-") and b["transaction_id"].startswith("TXN-")


@pytest.mark.parametrize("scenario,final", [("failed", "payment_failed"), ("pending", "payment_pending"),
                                            ("duplicate", "blocked_by_fraud"),
                                            ("amount_mismatch", "awaiting_human_approval")])
def test_business_outcomes_are_200(scenario, final):
    r = client.post("/workflow/purchase", json={**OK_BODY, "payment_scenario": scenario})
    assert r.status_code == 200 and r.json()["final_status"] == final


def test_unknown_course_is_404_with_structured_body():
    r = client.post("/workflow/purchase", json={**OK_BODY, "course_id": "C999"})
    assert r.status_code == 404
    assert r.json()["final_status"] == "unknown_course" and r.json()["order_id"] is None


@pytest.mark.parametrize("body", [{}, {"customer_id": "CUST0007"}, {**OK_BODY, "message": ""},
                                  {**OK_BODY, "payment_scenario": "steal"}, {**OK_BODY, "confirm_purchase": "maybe"}])
def test_invalid_requests_are_422(body):
    r = client.post("/workflow/purchase", json=body)
    assert r.status_code == 422 and "detail" in r.json()


def test_api_key_enforced_when_configured(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-secret")
    assert client.post("/workflow/purchase", json=OK_BODY).status_code == 401
    assert client.post("/workflow/purchase", json=OK_BODY, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/workflow/purchase", json=OK_BODY, headers={"X-API-Key": "test-secret"}).status_code == 200
    assert client.get("/health").status_code == 200        # health stays public


def test_individual_agent_endpoints():
    assert client.post("/agents/sales", json={"customer_message": "Python course?"}).json()["status"] == "ok"
    assert client.post("/agents/customer-intelligence",
                       json={"turns": [{"role": "customer", "text": "I want Python for AI"}]}).status_code == 200
    r = client.post("/agents/payment", json={"transaction_id": "T", "order_id": "O", "status": "success"})
    assert r.status_code == 200 and r.json()["data"]["payment_confirmed"] is False  # no evidence -> not confirmed
    r = client.post("/agents/fraud", json={"event": {"transaction_id": "T", "order_id": "O", "customer_id": "C",
                                                     "amount_tnd": 0, "timestamp": "2026-10-01T10:00:00"}})
    assert r.json()["data"]["action"] == "block"
    assert client.post("/agents/financial", json={"split": "eval"}).json()["data"]["calculation_engine"] == "pandas"


def test_agent_level_data_error_is_422():
    r = client.post("/agents/financial", json={"orders": [{"order_id": "X"}], "transactions": []})
    assert r.status_code == 422 and r.json()["status"] == "error"
