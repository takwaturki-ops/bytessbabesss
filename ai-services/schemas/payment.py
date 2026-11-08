from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field

FinalStatus = Literal["success", "failed", "pending", "requires_review"]


class PaymentEvent(BaseModel):
    """A SIMULATED payment provider event (webhook-like)."""

    transaction_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    status: str = Field(min_length=1, description="raw status reported by the (simulated) provider")
    amount_tnd: Optional[float] = None
    expected_amount_tnd: Optional[float] = None
    currency: Optional[str] = "TND"
    provider_reference: Optional[str] = None
    signature_valid: Optional[bool] = None
    failure_reason: Optional[str] = None
    payment_method: Optional[str] = None
    customer_id: Optional[str] = None
    course_id: Optional[str] = None
    timestamp: Optional[str] = None
    language: Optional[Literal["fr", "ar", "en", "darija"]] = None
    explain: bool = Field(True, description="if false, skip the LLM summary (saves tokens)")


class EvidenceChecks(BaseModel):
    status_reported_success: bool
    provider_reference_present: bool
    signature_valid: bool
    amount_matches_expected: bool
    currency_is_tnd: bool


class PaymentOutput(BaseModel):
    transaction_id: str
    order_id: str
    reported_status: str
    final_status: FinalStatus
    payment_confirmed: bool = Field(description="true ONLY when every evidence check passed")
    evidence: EvidenceChecks
    review_reasons: list[str]
    recommended_action: Literal["grant_access", "retry_payment", "wait_for_confirmation", "manual_review"]
    amount_tnd: Optional[float]
    currency: Optional[str]
    summary: str
    customer_message: str
    decided_by: Literal["deterministic_rules"] = "deterministic_rules"


class PaymentDraft(BaseModel):
    """The ONLY thing the LLM writes for this agent: wording. Status is never in this schema."""

    text_fields: ClassVar[tuple[str, ...]] = ("summary", "customer_message")
    summary: str = Field(description="one or two sentences for the internal team")
    customer_message: str = Field(description="short, polite message to the customer")
