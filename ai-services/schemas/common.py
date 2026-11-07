"""Schemas shared by all agents: the response envelope and execution metadata."""
from __future__ import annotations

from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)

DISCLAIMER = "Prototype output based on SIMULATED data. Not financial, legal or payment advice."


class AgentMeta(BaseModel):
    agent: str
    mode: Literal["mock", "live", "scripted", "fallback"] = Field(
        description="mock = no LLM call (templated text); live = real Claude call; "
                    "fallback = live call failed and deterministic text was used; scripted = test double")
    model: Optional[str] = None
    llm_used: bool = False
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    decision_source: Literal["deterministic", "llm", "hybrid"] = "deterministic"
    data_source: Literal["simulated"] = "simulated"
    guardrails_triggered: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


class AgentResponse(BaseModel, Generic[T]):
    """Uniform envelope returned by every `agent.run()` - easy to consume from n8n later."""

    agent: str
    status: Literal["ok", "error"]
    data: Optional[T] = None
    errors: list[str] = Field(default_factory=list)
    meta: AgentMeta


class Turn(BaseModel):
    role: Literal["customer", "agent"]
    text: str = Field(min_length=1, max_length=4000)


Intent = Literal["purchase_intent", "information_request", "price_objection", "course_comparison",
                 "payment_issue", "not_interested", "support_request"]
Objection = Literal["price", "time", "difficulty", "trust"]
Sentiment = Literal["positive", "neutral", "negative"]
