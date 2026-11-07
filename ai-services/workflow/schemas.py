"""Request / response contract of the purchase workflow (validated with Pydantic)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from schemas.common import AgentResponse, Turn
from schemas.financial import FinancialOutput
from schemas.fraud import FraudOutput, TxnEvent
from schemas.intel import CustomerInsights
from schemas.payment import PaymentOutput
from schemas.sales import SalesOutput

PaymentScenario = Literal[
    "success",              # provider confirms, all evidence valid
    "failed",               # card declined
    "pending",              # provider has not confirmed yet
    "amount_mismatch",      # provider reports a different amount than the order
    "duplicate",            # customer already paid this course minutes ago
    "repeated_attempts",    # 3 failed attempts just before -> human approval
    "excessive_attempts",   # 6 failed attempts just before -> block
    "invalid_signature",    # provider event signature is invalid -> block
    "suspicious_location",  # foreign IP on an unknown device -> human approval
]

FinalStatus = Literal[
    "completed",                 # payment confirmed, access can be granted
    "payment_failed",
    "payment_pending",
    "payment_requires_review",   # payment agent could not validate the evidence
    "awaiting_human_approval",   # fraud rules require a human decision
    "blocked_by_fraud",
    "no_purchase",               # customer did not confirm / changed their mind
    "unknown_course",
    "error",
]


class PurchaseWorkflowRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$", examples=["CUST0007"])
    message: str = Field(min_length=1, max_length=2000, examples=["I want to learn machine learning"])
    course_id: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9_\-]+$", examples=["C003"],
                                     description="course chosen by the customer; if omitted, the sales agent's top match is used")
    confirm_purchase: bool = Field(True, description="false = the customer has not confirmed (or changed their mind)")
    payment_scenario: PaymentScenario = Field("success", description="SIMULATED payment outcome to demonstrate")
    payment_method: Literal["card", "mobile_wallet", "bank_transfer"] = "card"
    discount_code: Optional[str] = Field(None, max_length=32)
    conversation_history: list[Turn] = Field(default_factory=list, max_length=50)
    previous_transactions: list[TxnEvent] = Field(
        default_factory=list, max_length=200,
        description="real recent transactions of this customer, supplied by the backend (agents never read the DB)")
    workflow_id: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9_\-]{4,40}$",
                                       description="optional, for reproducible demos/tests; generated if omitted")


class CourseRef(BaseModel):
    course_id: str
    title: str
    price_tnd: float = Field(description="catalog price (SIMULATED catalog)")


class TraceStep(BaseModel):
    step: int
    name: str
    agent: Optional[str] = None
    status: Literal["ok", "skipped", "stopped", "error"]
    decision: Optional[str] = None
    summary: str
    mode: Optional[str] = None
    duration_ms: int = 0


class FinancialImpact(BaseModel):
    revenue_before_tnd: float
    revenue_after_tnd: float
    revenue_delta_tnd: float = Field(description="> 0 only when the payment was confirmed")
    counted_as_revenue: bool


class PurchaseWorkflowResponse(BaseModel):
    workflow_id: str
    customer_id: str
    order_id: Optional[str] = None
    transaction_id: Optional[str] = None
    course: Optional[CourseRef] = None
    amount_tnd: Optional[float] = None
    final_status: FinalStatus
    purchase_confirmed: bool
    next_step: str
    sales_agent_result: Optional[AgentResponse[SalesOutput]] = None
    customer_intelligence_result: Optional[AgentResponse[CustomerInsights]] = None
    fraud_agent_result: Optional[AgentResponse[FraudOutput]] = None
    payment_agent_result: Optional[AgentResponse[PaymentOutput]] = None
    financial_analyst_result: Optional[AgentResponse[FinancialOutput]] = None
    financial_impact: Optional[FinancialImpact] = None
    execution_trace: list[TraceStep]
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    llm_mode: str
    data_notice: str = "SIMULATED data and payments - no real money is moved."
