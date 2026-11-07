from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field

Action = Literal["allow", "block", "require_human_approval"]


class TxnEvent(BaseModel):
    transaction_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    amount_tnd: float
    timestamp: str = Field(min_length=1, description="ISO-8601")
    status: Literal["success", "failed", "pending", "requires_review"] = "pending"
    expected_amount_tnd: Optional[float] = None
    currency: str = "TND"
    course_id: Optional[str] = None
    signature_valid: Optional[bool] = None
    ip_country: Optional[str] = None
    device_id: Optional[str] = None
    card_fingerprint: Optional[str] = None
    payment_method: Optional[str] = None
    provider_reference: Optional[str] = None


class CustomerContext(BaseModel):
    customer_id: Optional[str] = None
    home_country: str = "TN"
    known_devices: list[str] = Field(default_factory=list)


class FraudCheckInput(BaseModel):
    event: TxnEvent
    history: list[TxnEvent] = Field(default_factory=list, max_length=500,
                                    description="recent events (same customer/device/card), oldest first")
    customer_context: CustomerContext = Field(default_factory=CustomerContext)
    explain: bool = True


class RuleHit(BaseModel):
    rule_id: str
    severity: Literal["block", "review"]
    weight: int
    detail: str


class FraudOutput(BaseModel):
    transaction_id: str
    action: Action
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    flags: list[str]
    rule_hits: list[RuleHit]
    explanation: str
    alert_summary: Optional[str] = None
    decided_by: Literal["deterministic_rules"] = "deterministic_rules"
    llm_can_override: Literal[False] = False


class FraudDraft(BaseModel):
    """LLM writes wording only. `action` and `risk_score` are deliberately absent from this schema."""

    text_fields: ClassVar[tuple[str, ...]] = ("explanation", "alert_summary")
    explanation: str = Field(description="2-3 sentences explaining the triggered rules")
    alert_summary: str = Field(description="one-line alert title for the security team")
