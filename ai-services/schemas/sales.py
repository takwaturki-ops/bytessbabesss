from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field

from schemas.common import Intent, Turn

NextAction = Literal["present_courses", "answer_question", "handle_objection", "send_payment_link",
                     "route_to_payment_support", "route_to_customer_support", "end_conversation"]


class SalesInput(BaseModel):
    customer_message: str = Field(min_length=1, max_length=2000)
    conversation_history: list[Turn] = Field(default_factory=list, max_length=50)
    customer_id: Optional[str] = None
    customer_profile: Optional[dict] = Field(None, description="overrides the profile looked up by customer_id")
    channel: Literal["chat", "voice"] = "chat"


class CourseRecommendation(BaseModel):
    course_id: str
    title: str
    price_tnd: float
    level: str
    duration_weeks: int
    reason: str


class SalesOutput(BaseModel):
    reply: str
    detected_intent: Intent
    objection_type: Literal["price", "time", "difficulty", "trust", "none"]
    recommended_courses: list[CourseRecommendation] = Field(max_length=3)
    next_action: NextAction
    purchase_intent_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    catalog_grounded: bool = Field(description="true when every price/course in the reply was verified against the catalog")


class SalesDraft(BaseModel):
    text_fields: ClassVar[tuple[str, ...]] = ("reply",)
    reply: str = Field(description="reply to the customer, max ~90 words, in the customer's language")
    detected_intent: Intent
    objection_type: Literal["price", "time", "difficulty", "trust", "none"]
    recommended_course_ids: list[str] = Field(description="0-3 course_ids taken ONLY from `candidates`")
    recommendation_reasons: list[str] = Field(description="one short reason per recommended course")
    next_action: NextAction
    purchase_intent_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
