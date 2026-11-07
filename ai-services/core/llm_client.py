"""Shared LLM client used by every agent.

* mock mode  - never touches the network; agents supply a deterministic mock draft.
* live mode  - calls Claude through the official `anthropic` SDK with structured outputs
               (`messages.parse(output_format=PydanticModel)`), so responses are schema-validated.
* scripted   - test double that returns a pre-written draft (used to test guardrails against
               invalid / hallucinated LLM output without spending credits).

Every result records which mode produced it, so mock output is never mistaken for real LLM output.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from core.config import Settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Raised when a live LLM call fails or returns unusable output. Agents fall back to deterministic output."""


@dataclass
class LLMResult:
    parsed: BaseModel
    mode: str                    # "mock" | "live" | "scripted"
    model: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    stop_reason: str | None = None


class LLMClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self._client = None  # created lazily; mock mode never imports anthropic

    @property
    def mode(self) -> str:
        return self.settings.mode

    @property
    def model(self) -> str | None:
        return self.settings.model if self.mode == "live" else None

    # ------------------------------------------------------------------ public
    def generate(self, *, agent: str, system: str, payload: dict, output_model: type[T],
                 mock: Callable[[], T], max_tokens: int | None = None) -> LLMResult:
        if self.mode == "mock":
            return LLMResult(parsed=mock(), mode="mock", model=None)
        return self._live(agent, system, payload, output_model, max_tokens or self.settings.max_tokens)

    # ------------------------------------------------------------------ live
    def _get_client(self):
        if self._client is None:
            import os

            import anthropic  # imported only in live mode

            kwargs = {"timeout": self.settings.timeout_s, "max_retries": self.settings.max_retries}
            # Team convention (repo README) names the key LLM_API_KEY; ANTHROPIC_API_KEY also works.
            key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY")
            if key:
                kwargs["api_key"] = key
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def _live(self, agent: str, system: str, payload: dict, output_model: type[T], max_tokens: int) -> LLMResult:
        import anthropic

        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
        t0 = time.perf_counter()
        try:
            client = self._get_client()
        except Exception as e:  # e.g. no credentials configured at all
            raise LLMError(f"cannot create Anthropic client ({type(e).__name__}) - set ANTHROPIC_API_KEY "
                           f"or use LLM_MODE=mock") from e
        try:
            resp = client.messages.parse(
                model=self.settings.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                output_format=output_model,
                output_config={"effort": self.settings.effort},
            )
        except anthropic.AuthenticationError as e:
            raise LLMError("authentication failed - set ANTHROPIC_API_KEY or switch LLM_MODE=mock") from e
        except anthropic.NotFoundError as e:
            raise LLMError(f"model not found: {self.settings.model}") from e
        except anthropic.RateLimitError as e:
            raise LLMError("rate limited by the API") from e
        except anthropic.BadRequestError as e:
            raise LLMError(f"bad request: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"API error {e.status_code}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("network error contacting the API") from e
        except ValidationError as e:
            raise LLMError(f"LLM output failed schema validation: {e.error_count()} errors") from e
        except anthropic.AnthropicError as e:  # any other SDK error
            raise LLMError(f"Anthropic SDK error: {type(e).__name__}") from e
        except TypeError as e:  # the SDK raises TypeError when no credentials can be resolved
            raise LLMError(f"no Anthropic credentials found ({e}) - set ANTHROPIC_API_KEY or use LLM_MODE=mock") from e
        latency = int((time.perf_counter() - t0) * 1000)

        usage = getattr(resp, "usage", None)
        result_kwargs = dict(
            mode="live", model=self.settings.model, latency_ms=latency, stop_reason=resp.stop_reason,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )
        self._log_usage(agent, result_kwargs)
        if resp.stop_reason == "refusal":
            raise LLMError("model declined the request (refusal)")
        if resp.stop_reason == "max_tokens":
            raise LLMError("output truncated at max_tokens")
        parsed = getattr(resp, "parsed_output", None)
        if parsed is None:
            raise LLMError("no structured output returned")
        return LLMResult(parsed=parsed, **result_kwargs)

    def _log_usage(self, agent: str, info: dict) -> None:
        try:
            self.settings.usage_log.parent.mkdir(parents=True, exist_ok=True)
            rec = {"ts": datetime.now(timezone.utc).isoformat(), "agent": agent, **info}
            with self.settings.usage_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError:
            pass


@dataclass
class ScriptedLLMClient(LLMClient):
    """Test double: returns a fixed draft (dict) as if the LLM produced it. Used to test guardrails."""

    draft: dict[str, Any] = field(default_factory=dict)
    fail: bool = False

    def __post_init__(self):
        self.settings = Settings(mode="live", model="scripted-test-double")
        self._client = None

    @property
    def mode(self) -> str:
        return "scripted"

    def generate(self, *, agent, system, payload, output_model, mock, max_tokens=None) -> LLMResult:
        if self.fail:
            raise LLMError("scripted failure")
        try:
            parsed = output_model.model_validate(self.draft)
        except ValidationError as e:
            raise LLMError(f"LLM output failed schema validation: {e.error_count()} errors") from e
        return LLMResult(parsed=parsed, mode="scripted", model="scripted-test-double")


_default: LLMClient | None = None


def get_default_client() -> LLMClient:
    global _default
    if _default is None:
        _default = LLMClient()
    return _default
