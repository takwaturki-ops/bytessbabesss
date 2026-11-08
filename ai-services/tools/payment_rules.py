"""Deterministic payment status interpretation. The LLM never decides payment status."""
from __future__ import annotations

from schemas.payment import EvidenceChecks, PaymentEvent

STATUS_ALIASES = {
    "success": "success", "succeeded": "success", "paid": "success", "completed": "success", "captured": "success",
    "failed": "failed", "failure": "failed", "declined": "failed", "error": "failed", "cancelled": "failed",
    "canceled": "failed", "expired": "failed",
    "pending": "pending", "processing": "pending", "in_progress": "pending", "authorized": "pending",
    "requires_review": "requires_review", "review": "requires_review", "on_hold": "requires_review",
}
ACTION = {"success": "grant_access", "failed": "retry_payment", "pending": "wait_for_confirmation",
          "requires_review": "manual_review"}
AMOUNT_TOLERANCE = 0.01


def interpret(ev: PaymentEvent) -> tuple[str, bool, EvidenceChecks, list[str]]:
    """Return (final_status, payment_confirmed, evidence, review_reasons)."""
    normalized = STATUS_ALIASES.get(ev.status.strip().lower())
    reasons: list[str] = []
    amount_ok = (ev.amount_tnd is not None and ev.expected_amount_tnd is not None
                 and ev.amount_tnd > 0 and abs(ev.amount_tnd - ev.expected_amount_tnd) <= AMOUNT_TOLERANCE)
    evidence = EvidenceChecks(
        status_reported_success=normalized == "success",
        provider_reference_present=bool(ev.provider_reference and ev.provider_reference.strip()),
        signature_valid=ev.signature_valid is True,
        amount_matches_expected=amount_ok,
        currency_is_tnd=(ev.currency or "").upper() == "TND",
    )

    if normalized is None:
        return "requires_review", False, evidence, [f"unknown_status:{ev.status}"]
    if normalized == "failed":
        return "failed", False, evidence, []
    if ev.amount_tnd is not None and ev.amount_tnd <= 0:
        return "requires_review", False, evidence, ["invalid_amount"]
    if normalized == "pending":
        return "pending", False, evidence, []
    if normalized == "requires_review":
        reasons.append(f"provider_flagged:{ev.failure_reason or 'unspecified'}")
        if not evidence.signature_valid:
            reasons.append("signature_invalid_or_missing")
        if not amount_ok:
            reasons.append("amount_mismatch_or_missing")
        return "requires_review", False, evidence, reasons

    # Provider claims success: require ALL evidence before confirming.
    if not evidence.provider_reference_present:
        reasons.append("missing_provider_reference")
    if not evidence.signature_valid:
        reasons.append("signature_invalid_or_missing")
    if ev.amount_tnd is None or ev.expected_amount_tnd is None:
        reasons.append("amount_or_expected_amount_missing")
    elif not amount_ok:
        reasons.append("amount_mismatch")
    if not evidence.currency_is_tnd:
        reasons.append("currency_not_tnd")
    if reasons:
        return "requires_review", False, evidence, reasons
    return "success", True, evidence, []
