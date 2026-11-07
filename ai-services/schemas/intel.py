from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from schemas.common import Intent, Objection, Sentiment, Turn

Stage = Literal["awareness", "consideration", "decision", "purchased", "support", "lost"]


class IntelInput(BaseModel):
    turns: list[Turn] = Field(min_length=1, max_length=60)
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None

    @field_validator("turns")
    @classmethod
    def needs_customer_turn(cls, v: list[Turn]) -> list[Turn]:
        if not any(t.role == "customer" for t in v):
            raise ValueError("at least one customer turn is required")
        return v


class CustomerInsights(BaseModel):
    conversation_id: Optional[str]
    customer_id: Optional[str]
    primary_intent: Intent
    needs: list[str] = Field(max_length=6)
    motivations: list[str] = Field(max_length=6)
    objections: list[Objection]
    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1, le=1)
    interest_score: int = Field(ge=0, le=100)
    satisfaction_score: int = Field(ge=0, le=100)
    purchase_stage: Stage
    mentioned_course_ids: list[str]
    recommended_follow_up: str
    summary: str
    confidence: float = Field(ge=0, le=1)


class IntelDraft(BaseModel):
    text_fields: ClassVar[tuple[str, ...]] = ("summary", "recommended_follow_up")
    primary_intent: Intent
    needs: list[str] = Field(description="concrete needs, max 6 short phrases")
    motivations: list[str] = Field(description="why they want to learn, max 6 short phrases")
    objections: list[Objection]
    sentiment: Sentiment
    sentiment_score: float = Field(description="-1 (very negative) to 1 (very positive)")
    interest_score: int = Field(description="0-100 likelihood/interest to buy")
    satisfaction_score: int = Field(description="0-100 satisfaction with the interaction")
    purchase_stage: Stage
    mentioned_course_ids: list[str]
    recommended_follow_up: str
    summary: str
    confidence: float
