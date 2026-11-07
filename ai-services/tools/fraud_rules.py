"""Deterministic fraud rules. These are the ONLY source of allow / block / require_human_approval decisions."""
from __future__ import annotations

from datetime import datetime, timedelta

from schemas.fraud import FraudCheckInput, RuleHit

# Thresholds (tunable, documented in README)
REPEATED_REVIEW, REPEATED_BLOCK, REPEATED_WINDOW_MIN = 3, 5, 30
VELOCITY_ORDERS, VELOCITY_WINDOW_MIN = 3, 15
CARDS_REVIEW, CARDS_WINDOW_MIN = 3, 60
DUPLICATE_WINDOW_H = 24
HIGH_AMOUNT_TND = 1500.0
AMOUNT_TOLERANCE = 0.01


def _t(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)


def evaluate(inp: FraudCheckInput) -> list[RuleHit]:
    ev, hist, ctx = inp.event, inp.history, inp.customer_context
    now = _t(ev.timestamp)
    prior = [h for h in hist if h.transaction_id != ev.transaction_id and _t(h.timestamp) <= now]
    hits: list[RuleHit] = []

    def within(h, minutes: float) -> bool:
        return now - _t(h.timestamp) <= timedelta(minutes=minutes)

    # 1. Invalid amount
    if ev.amount_tnd <= 0:
        hits.append(RuleHit(rule_id="INVALID_AMOUNT", severity="block", weight=60,
                            detail=f"amount {ev.amount_tnd} TND is not positive"))

    # 2. Duplicate payment: order already paid, or same customer+course paid in last 24h
    if ev.status in ("success", "pending"):
        dup = [h for h in prior if h.status == "success" and (
            h.order_id == ev.order_id or (ev.course_id and h.course_id == ev.course_id
                                          and h.customer_id == ev.customer_id and within(h, DUPLICATE_WINDOW_H * 60)))]
        if dup:
            hits.append(RuleHit(rule_id="DUPLICATE_PAYMENT", severity="block", weight=70,
                                detail=f"already paid by {dup[0].transaction_id} (order {dup[0].order_id})"))

    # 3. Repeated failed attempts (same customer or same card) in a short window
    fails = [h for h in prior if h.status == "failed" and within(h, REPEATED_WINDOW_MIN) and (
        h.customer_id == ev.customer_id or (ev.card_fingerprint and h.card_fingerprint == ev.card_fingerprint))]
    if len(fails) >= REPEATED_BLOCK:
        hits.append(RuleHit(rule_id="REPEATED_ATTEMPTS", severity="block", weight=50,
                            detail=f"{len(fails)} failed attempts in {REPEATED_WINDOW_MIN} min"))
    elif len(fails) >= REPEATED_REVIEW:
        hits.append(RuleHit(rule_id="REPEATED_ATTEMPTS", severity="review", weight=30,
                            detail=f"{len(fails)} failed attempts in {REPEATED_WINDOW_MIN} min"))

    # 4. Amount mismatch vs expected (catalog price after discount)
    if ev.amount_tnd > 0 and ev.expected_amount_tnd is not None and \
            abs(ev.amount_tnd - ev.expected_amount_tnd) > AMOUNT_TOLERANCE:
        hits.append(RuleHit(rule_id="AMOUNT_MISMATCH", severity="review", weight=35,
                            detail=f"paid {ev.amount_tnd} TND, expected {ev.expected_amount_tnd} TND"))

    # 5. Invalid signature on the provider event
    if ev.signature_valid is False:
        sev = "block" if ev.status == "success" else "review"
        hits.append(RuleHit(rule_id="INVALID_SIGNATURE", severity=sev, weight=60 if sev == "block" else 30,
                            detail=f"provider signature invalid on a '{ev.status}' event"))

    # 6. Currency
    if ev.currency.upper() != "TND":
        hits.append(RuleHit(rule_id="CURRENCY_MISMATCH", severity="review", weight=25,
                            detail=f"currency {ev.currency} instead of TND"))

    # 7. Device velocity: many different orders from one device in a short window
    if ev.device_id:
        orders = {h.order_id for h in prior if h.device_id == ev.device_id and h.order_id != ev.order_id
                  and within(h, VELOCITY_WINDOW_MIN)}
        if len(orders) >= VELOCITY_ORDERS:
            hits.append(RuleHit(rule_id="DEVICE_VELOCITY", severity="review", weight=30,
                                detail=f"{len(orders)} other orders from device {ev.device_id} in {VELOCITY_WINDOW_MIN} min"))

    # 8. Geo mismatch on an unknown device
    if ev.ip_country and ev.ip_country.upper() != ctx.home_country.upper() and ev.device_id not in ctx.known_devices:
        hits.append(RuleHit(rule_id="GEO_MISMATCH", severity="review", weight=30,
                            detail=f"IP country {ev.ip_country} differs from {ctx.home_country} on an unknown device"))

    # 9. Many different cards for one customer
    cards = {h.card_fingerprint for h in prior if h.customer_id == ev.customer_id and h.card_fingerprint
             and within(h, CARDS_WINDOW_MIN)}
    if ev.card_fingerprint:
        cards.add(ev.card_fingerprint)
    if len(cards) >= CARDS_REVIEW:
        hits.append(RuleHit(rule_id="MULTIPLE_CARDS", severity="review", weight=30,
                            detail=f"{len(cards)} distinct cards in {CARDS_WINDOW_MIN} min"))

    # 10. Unusually high amount
    if ev.amount_tnd > HIGH_AMOUNT_TND:
        hits.append(RuleHit(rule_id="HIGH_AMOUNT", severity="review", weight=20,
                            detail=f"amount {ev.amount_tnd} TND above {HIGH_AMOUNT_TND} TND"))
    return hits


def decide(hits: list[RuleHit]) -> tuple[str, int, str]:
    """Return (action, risk_score, risk_level). Any block rule -> block; any review rule -> human approval."""
    score = min(100, sum(h.weight for h in hits))
    if any(h.severity == "block" for h in hits):
        return "block", max(score, 70), "high"
    if hits:
        return "require_human_approval", max(score, 30), "medium"
    return "allow", score, "low"
