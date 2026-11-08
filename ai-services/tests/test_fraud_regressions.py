"""Regression tests for the fraud fixes (timezones, history status validation, transaction metadata).

Thresholds are unchanged: 3 failed attempts in 30 min -> human review, 5 -> block.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agents import FraudAgent
from api.main import app
from core.config import Settings
from core.llm_client import LLMClient
from core.timeutil import parse_to_utc, to_utc_iso
from schemas.fraud import FraudCheckInput, HistoryTxn, TxnEvent
from tools import fraud_rules
from workflow import PurchaseWorkflow, PurchaseWorkflowRequest

TUNIS = timezone(timedelta(hours=1))
CUST = "CUST-FRAUD-001"


@pytest.fixture(scope="module")
def wf():
    return PurchaseWorkflow(LLMClient(Settings(mode="mock")))


@pytest.fixture(scope="module")
def fraud():
    return FraudAgent(LLMClient(Settings(mode="mock")))


def fmt(dt_utc: datetime, style: str) -> str:
    """Same instant written three ways: 'z' (UTC Z), 'tunis' (+01:00 local time), 'naive' (UTC, no offset)."""
    if style == "z":
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    if style == "tunis":
        return dt_utc.astimezone(TUNIS).isoformat()
    return dt_utc.replace(tzinfo=None).isoformat()


def failures(n: int, style: str, base: datetime | None = None, **over) -> list[dict]:
    base = base or datetime.now(timezone.utc).replace(microsecond=0)
    return [{"transaction_id": f"PREV-{i}", "order_id": f"ORD-PREV-{i}", "customer_id": CUST, "course_id": "C003",
             "amount_tnd": 349.0, "status": "failed", "device_id": "DEV-X", "card_fingerprint": "fp_x",
             "timestamp": fmt(base - timedelta(minutes=3 * (i + 1)), style), **over} for i in range(n)]


def buy(wf, **kw):
    return wf.run(PurchaseWorkflowRequest(customer_id=CUST, message="I want to buy Machine Learning Essentials",
                                          course_id="C003", payment_scenario="success", **kw))


# --------------------------------------------------------------------------- 1. timezone helper
def test_offset_is_converted_not_dropped():
    assert parse_to_utc("2026-11-08T10:00:00+01:00") == datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)
    assert to_utc_iso("2026-11-08T10:00:00+01:00") == "2026-11-08T09:00:00+00:00"


def test_z_and_naive_are_utc():
    assert to_utc_iso("2026-11-08T09:00:00Z") == "2026-11-08T09:00:00+00:00"
    assert to_utc_iso("2026-11-08T09:00:00") == "2026-11-08T09:00:00+00:00"


@pytest.mark.parametrize("bad", ["", "   ", "yesterday", "08/11/2026 10:00", "2026-13-40T99:00:00"])
def test_invalid_timestamps_raise(bad):
    with pytest.raises(ValueError):
        parse_to_utc(bad)


def test_old_bug_is_fixed_in_rules():
    # Before the fix _t() dropped "+01:00" and returned 10:00; it must be 09:00 UTC.
    assert fraud_rules._t("2026-11-08T10:00:00+01:00") == datetime(2026, 11, 8, 9, 0)


# --------------------------------------------------------------------------- 1. timezone in the fraud agent
@pytest.mark.parametrize("n,action", [(2, "allow"), (3, "require_human_approval"), (5, "block")])
def test_fraud_agent_same_decision_for_equivalent_timestamps(fraud, n, action):
    now = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)
    results = []
    for style in ("z", "tunis", "naive"):
        event = {"transaction_id": "T-NOW", "order_id": "O-NOW", "customer_id": CUST, "amount_tnd": 349.0,
                 "expected_amount_tnd": 349.0, "status": "success", "timestamp": fmt(now, style)}
        r = fraud.run({"event": event, "history": failures(n, style, now)})
        assert r.status == "ok"
        results.append((r.data.action, r.data.flags, r.data.risk_score))
    assert results[0] == results[1] == results[2]
    assert results[0][0] == action


def test_mixed_offsets_in_one_request(fraud):
    """Event in UTC, history in Tunis time: history must be counted, not silently dropped."""
    now = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)
    event = {"transaction_id": "T-NOW", "order_id": "O-NOW", "customer_id": CUST, "amount_tnd": 349.0,
             "status": "success", "timestamp": fmt(now, "z")}
    r = fraud.run({"event": event, "history": failures(3, "tunis", now)})
    assert r.data.action == "require_human_approval" and r.meta.warnings == []


def test_future_history_is_reported_not_silent(fraud):
    now = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)
    event = {"transaction_id": "T-NOW", "order_id": "O-NOW", "customer_id": CUST, "amount_tnd": 349.0,
             "status": "success", "timestamp": fmt(now, "z")}
    # Tunis local wall-clock written WITHOUT offset -> read as UTC -> 1 h in the future
    wrong = [dict(h, timestamp=(now.astimezone(TUNIS) - timedelta(minutes=5)).replace(tzinfo=None).isoformat())
             for h in failures(3, "z", now)]
    r = fraud.run({"event": event, "history": wrong})
    assert r.data.action == "allow"                                   # rule behaviour unchanged
    assert any(w.startswith("history_after_event_ignored:3") for w in r.meta.warnings)


def test_invalid_timestamp_is_an_input_error(fraud):
    r = fraud.run({"event": {"transaction_id": "T", "order_id": "O", "customer_id": "C", "amount_tnd": 10,
                             "timestamp": "not-a-date"}})
    assert r.status == "error" and "invalid_input" in r.errors


# --------------------------------------------------------------------------- 1+4. workflow thresholds (original case)
def test_original_two_failure_case_still_allowed(wf):
    r = buy(wf, previous_transactions=failures(2, "z"))
    assert r.fraud_agent_result.data.action == "allow" and r.final_status == "completed"
    assert r.financial_impact.revenue_delta_tnd == 349.0


def test_three_failures_require_human_approval(wf):
    r = buy(wf, previous_transactions=failures(3, "z"))
    assert r.fraud_agent_result.data.action == "require_human_approval"
    assert "REPEATED_ATTEMPTS" in r.fraud_agent_result.data.flags
    assert r.final_status == "awaiting_human_approval" and r.payment_agent_result is None
    assert r.financial_impact.revenue_delta_tnd == 0


def test_five_failures_are_blocked(wf):
    r = buy(wf, previous_transactions=failures(5, "z"))
    assert r.fraud_agent_result.data.action == "block" and r.final_status == "blocked_by_fraud"
    assert r.payment_agent_result is None and r.financial_impact.revenue_delta_tnd == 0


@pytest.mark.parametrize("n", [2, 3, 5])
def test_workflow_same_decision_for_tunis_utc_and_naive_history(wf, n):
    base = datetime.now(timezone.utc).replace(microsecond=0)
    decisions = {style: (lambda r: (r.fraud_agent_result.data.action, r.final_status))(
        buy(wf, previous_transactions=failures(n, style, base))) for style in ("z", "tunis", "naive")}
    assert len(set(decisions.values())) == 1, decisions


# --------------------------------------------------------------------------- 3. status validation
def test_history_status_is_required():
    with pytest.raises(ValidationError):
        HistoryTxn(transaction_id="T", order_id="O", customer_id="C", amount_tnd=1, timestamp="2026-11-08T09:00:00Z")
    hist = failures(1, "z")
    del hist[0]["status"]
    with pytest.raises(ValidationError):
        PurchaseWorkflowRequest(customer_id=CUST, message="buy", previous_transactions=hist)


@pytest.mark.parametrize("bad", ["declined", "FAILEDX", "", "ok", None, 1])
def test_invalid_history_status_rejected(bad):
    with pytest.raises(ValidationError):
        HistoryTxn(transaction_id="T", order_id="O", customer_id="C", amount_tnd=1,
                   timestamp="2026-11-08T09:00:00Z", status=bad)


@pytest.mark.parametrize("raw,norm", [("FAILED", "failed"), (" Success ", "success"), ("Requires_Review", "requires_review")])
def test_status_is_case_insensitive(raw, norm):
    h = HistoryTxn(transaction_id="T", order_id="O", customer_id="C", amount_tnd=1,
                   timestamp="2026-11-08T09:00:00Z", status=raw)
    assert h.status == norm


def test_current_event_keeps_backward_compatible_default():
    e = TxnEvent(transaction_id="T", order_id="O", customer_id="C", amount_tnd=1, timestamp="2026-11-08T09:00:00Z")
    assert e.status == "pending"


def test_uppercase_failed_history_counts_as_failed(wf):
    r = buy(wf, previous_transactions=failures(3, "z", status="FAILED"))
    assert r.fraud_agent_result.data.action == "require_human_approval"


def test_api_rejects_history_without_status():
    hist = failures(2, "z")
    del hist[1]["status"]
    r = TestClient(app).post("/workflow/purchase", json={"customer_id": CUST, "message": "buy", "course_id": "C003",
                                                         "previous_transactions": hist})
    assert r.status_code == 422
    assert any("status" in str(d["loc"]) for d in r.json()["detail"])


def test_fraud_endpoint_rejects_invalid_history_status():
    body = {"event": {"transaction_id": "T", "order_id": "O", "customer_id": "C", "amount_tnd": 10,
                      "timestamp": "2026-11-08T09:00:00Z"},
            "history": [{"transaction_id": "H", "order_id": "O2", "customer_id": "C", "amount_tnd": 10,
                         "timestamp": "2026-11-08T08:50:00Z", "status": "declined"}]}
    assert TestClient(app).post("/agents/fraud", json=body).status_code == 422


# --------------------------------------------------------------------------- 2. metadata propagation
def test_defaults_preserved_when_metadata_omitted(wf):
    r = buy(wf)
    assert r.final_status == "completed"
    assert not any("caller-supplied metadata" in w for w in r.warnings)


def test_supplied_card_fingerprint_reaches_fraud_rules(wf):
    """Failures from OTHER customer ids on the same card only match if the real card is passed through."""
    hist = failures(3, "z", customer_id="SOMEONE-ELSE", card_fingerprint="fp_REAL_CARD")
    assert buy(wf, previous_transactions=hist).fraud_agent_result.data.action == "allow"   # synthetic card: no match
    r = buy(wf, previous_transactions=hist, card_fingerprint="fp_REAL_CARD")
    assert r.fraud_agent_result.data.action == "require_human_approval"
    assert any("untrusted" in w and "card_fingerprint" in w for w in r.warnings)


def test_supplied_device_reaches_velocity_rule(wf):
    base = datetime.now(timezone.utc).replace(microsecond=0)
    hist = [{"transaction_id": f"V{i}", "order_id": f"ORD-V{i}", "customer_id": f"OTHER-{i}", "amount_tnd": 349.0,
             "status": "success", "device_id": "DEV-SHARED", "timestamp": fmt(base - timedelta(minutes=i + 1), "z")}
            for i in range(3)]
    assert buy(wf, previous_transactions=hist).fraud_agent_result.data.action == "allow"
    r = buy(wf, previous_transactions=hist, device_id="DEV-SHARED")
    assert "DEVICE_VELOCITY" in r.fraud_agent_result.data.flags


def test_supplied_ip_and_known_devices_drive_geo_rule(wf):
    r = buy(wf, ip_country="ng", device_id="DEV-NEW", known_devices=["DEV-OLD"])
    assert "GEO_MISMATCH" in r.fraud_agent_result.data.flags and r.final_status == "awaiting_human_approval"
    r = buy(wf, ip_country="NG", device_id="DEV-OLD", known_devices=["DEV-OLD"])
    assert r.fraud_agent_result.data.action == "allow"          # travelling customer on a known device


def test_suspicious_location_scenario_still_works_without_metadata(wf):
    r = wf.run(PurchaseWorkflowRequest(customer_id=CUST, message="buy", course_id="C003",
                                       payment_scenario="suspicious_location"))
    assert "GEO_MISMATCH" in r.fraud_agent_result.data.flags


@pytest.mark.parametrize("bad", [{"ip_country": "TUN"}, {"ip_country": "1N"}, {"device_id": "dev with spaces"},
                                 {"card_fingerprint": "4111 1111 1111 1111"}, {"device_id": "x" * 200}])
def test_invalid_metadata_rejected(bad):
    with pytest.raises(ValidationError):
        PurchaseWorkflowRequest(customer_id=CUST, message="buy", **bad)
