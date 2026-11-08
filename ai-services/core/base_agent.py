"""BaseAgent: validate input -> deterministic processing -> optional LLM draft -> guardrails -> validated output."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Callable, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from core.config import ROOT
from core.llm_client import LLMClient, LLMError, get_default_client
from schemas.common import AgentMeta, AgentResponse

I = TypeVar("I", bound=BaseModel)
O = TypeVar("O", bound=BaseModel)
D = TypeVar("D", bound=BaseModel)

log = logging.getLogger("9antra.agents")
MOCK_PREFIX = "[MOCK] "
FALLBACK_PREFIX = "[FALLBACK] "


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    return (ROOT / "prompts" / f"{name}.md").read_text(encoding="utf-8").strip()


def _prefix_text(draft: BaseModel, fields: tuple[str, ...], prefix: str) -> BaseModel:
    updates = {}
    for f in fields:
        v = getattr(draft, f, None)
        if isinstance(v, str) and not v.startswith(prefix):
            updates[f] = prefix + v
        elif isinstance(v, list) and v and all(isinstance(x, str) for x in v):
            updates[f] = [x if x.startswith(prefix) else prefix + x for x in v]
    return draft.model_copy(update=updates)


class BaseAgent(ABC, Generic[I, O]):
    name: ClassVar[str]
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]
    prompt_name: ClassVar[str]
    max_tokens: ClassVar[int | None] = None

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or get_default_client()
        self.system_prompt = load_prompt(self.prompt_name)

    # ------------------------------------------------------------------ public interface
    def run(self, input_data: Any) -> AgentResponse:
        t0 = time.perf_counter()
        meta = AgentMeta(agent=self.name, mode=self.llm.mode, model=self.llm.model)
        envelope = AgentResponse[self.output_model]  # type: ignore[name-defined]
        try:
            inp = input_data if isinstance(input_data, self.input_model) else self.input_model.model_validate(input_data)
        except ValidationError as e:
            meta.latency_ms = int((time.perf_counter() - t0) * 1000)
            errs = [f"{'.'.join(map(str, err['loc'])) or 'input'}: {err['msg']}" for err in e.errors()]
            return envelope(agent=self.name, status="error", errors=["invalid_input"] + errs, meta=meta)
        try:
            out = self.process(inp, meta)
            out = self.output_model.model_validate(out.model_dump())  # final validation of the output contract
        except Exception as e:  # never crash the caller (n8n); report a structured error instead
            if isinstance(e, ValueError):  # bad data supplied by the caller: no stack trace needed
                log.warning("%s rejected input data: %s", self.name, e)
            else:
                log.exception("%s failed", self.name)
            meta.latency_ms = int((time.perf_counter() - t0) * 1000)
            return envelope(agent=self.name, status="error", errors=[f"internal_error: {type(e).__name__}: {e}"],
                            meta=meta)
        meta.latency_ms = int((time.perf_counter() - t0) * 1000)
        return envelope(agent=self.name, status="ok", data=out, meta=meta)

    # ------------------------------------------------------------------ for subclasses
    @abstractmethod
    def process(self, inp: I, meta: AgentMeta) -> O:
        ...

    def draft(self, *, payload: dict, draft_model: type[D], mock: Callable[[], D], meta: AgentMeta,
              text_fields: tuple[str, ...] = ()) -> D:
        """Get an LLM draft (live) or a labelled deterministic draft (mock / fallback)."""
        try:
            res = self.llm.generate(agent=self.name, system=self.system_prompt, payload=payload,
                                    output_model=draft_model, mock=mock, max_tokens=self.max_tokens)
        except LLMError as e:
            meta.mode = "fallback"
            meta.warnings.append(f"llm_unavailable: {e}")
            return _prefix_text(mock(), text_fields, FALLBACK_PREFIX)  # type: ignore[return-value]
        if res.mode == "mock":
            return _prefix_text(res.parsed, text_fields, MOCK_PREFIX)  # type: ignore[return-value]
        meta.llm_calls += 1
        meta.llm_used = True
        meta.input_tokens += res.input_tokens
        meta.output_tokens += res.output_tokens
        return res.parsed  # type: ignore[return-value]
