from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field


class FinancialQuery(BaseModel):
    question: str = Field("Give me an overview of sales and payments.", min_length=3, max_length=500)
    split: Literal["dev", "eval", "all"] = "dev"
    date_from: Optional[str] = Field(None, description="ISO date, inclusive")
    date_to: Optional[str] = Field(None, description="ISO date, inclusive")
    orders: Optional[list[dict]] = Field(None, description="optional inline orders (overrides split)")
    transactions: Optional[list[dict]] = Field(None, description="optional inline transactions (overrides split)")
    explain: bool = True


class Breakdown(BaseModel):
    key: str
    label: str
    revenue_tnd: float
    paid_orders: int


class FinancialMetrics(BaseModel):
    total_orders: int
    paid_orders: int
    failed_orders: int
    pending_orders: int
    review_orders: int
    gross_revenue_tnd: float
    list_value_of_paid_orders_tnd: float
    discount_total_tnd: float
    average_order_value_tnd: float
    order_conversion_rate: float = Field(description="paid orders / total orders (0-1)")
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    pending_transactions: int
    review_transactions: int
    payment_success_rate: float = Field(description="successful transactions / all transactions (0-1)")
    first_attempt_success_rate: float = Field(description="orders paid on attempt 1 / orders with transactions")
    pending_amount_tnd: float
    at_risk_amount_tnd: float = Field(description="amount of orders in requires_review")
    conversation_conversion_rate: Optional[float] = Field(None, description="converted conversations / all (0-1)")
    revenue_by_course: list[Breakdown]
    revenue_by_category: list[Breakdown]
    revenue_by_payment_method: list[Breakdown]
    revenue_by_month: list[Breakdown]
    failure_reasons: dict[str, int]


class DataScope(BaseModel):
    source: str
    n_orders: int
    n_transactions: int
    date_from: Optional[str]
    date_to: Optional[str]


class FinancialOutput(BaseModel):
    question: str
    metrics: FinancialMetrics
    insights: list[str]
    narrative: str
    data_scope: DataScope
    calculation_engine: Literal["pandas"] = "pandas"


class FinancialDraft(BaseModel):
    text_fields: ClassVar[tuple[str, ...]] = ("narrative", "insights")
    narrative: str = Field(description="3-5 sentences answering the question using only the given numbers")
    insights: list[str] = Field(description="2-4 short actionable insights", max_length=5)
