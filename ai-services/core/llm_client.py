"""Shared LLM client used by every agent.

* mock mode  - never touches the network; agents supply a deterministic mock draft.
* live mode  - LLM_PROVIDER=anthropic (default): calls Claude through the official `anthropic` SDK with
               structured outputs (`messages.parse(output_format=PydanticModel)`).
               LLM_PROVIDER=deepseek: calls the DeepSeek chat API (OpenAI-compatible) in JSON mode, with the
               Pydantic JSON Schema in the system prompt, then validates the JSON with the same Pydantic model.
               Either way a response that does not match the schema raises LLMError -> deterministic fallback.
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
    def __init__(self, settings: Settings | None = None, http_client: Any = None):
        self.settings = settings or Settings.from_env()
        self._client = None  # created lazily; mock mode never imports anthropic
        self._http = http_client  # DeepSeek: httpx.Client, created lazily (tests inject one with a fake transport)

    @property
    def provider(self) -> str | None:
        return self.settings.provider if self.mode == "live" else None

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
        if self.settings.provider == "deepseek":
            return self._live_deepseek(agent, system, payload, output_model, max_tokens or self.settings.max_tokens)
        return self._live(agent, system, payload, output_model, max_tokens or self.settings.max_tokens)

    # ------------------------------------------------------------------ live: DeepSeek
    _DEEPSEEK_RETRY_STATUS = {429, 500, 502, 503, 504}
    _DEEPSEEK_ERRORS = {
        400: "bad request", 401: "authentication failed - check DEEPSEEK_API_KEY or switch LLM_MODE=mock",
        402: "insufficient DeepSeek balance", 422: "invalid request parameters", 429: "rate limited by the API",
    }

    def _deepseek_http(self):
        if self._http is None:
            import httpx

            self._http = httpx.Client(base_url=self.settings.base_url or "https://api.deepseek.com",
                                      timeout=self.settings.timeout_s)
        return self._http

    def _live_deepseek(self, agent: str, system: str, payload: dict, output_model: type[T],
                       max_tokens: int) -> LLMResult:
        import os

        import httpx

        key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY")
        if not key:
            raise LLMError("no DeepSeek API key - set DEEPSEEK_API_KEY or use LLM_MODE=mock")

        schema = json.dumps(output_model.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
        system_json = (
            f"{system}\n\n## Output format\n"
            "Reply with ONE json object and nothing else (no markdown fences, no text before or after). "
            f"It must validate against this JSON Schema:\n{schema}"
        )
        body = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_json},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        t0 = time.perf_counter()
        resp = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                resp = self._deepseek_http().post("/chat/completions", json=body, headers=headers)
            except httpx.TimeoutException as e:
                if attempt < self.settings.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMError("DeepSeek API timeout") from e
            except httpx.HTTPError as e:
                if attempt < self.settings.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMError("network error contacting the DeepSeek API") from e
            if resp.status_code in self._DEEPSEEK_RETRY_STATUS and attempt < self.settings.max_retries:
                time.sleep(2 ** attempt)
                continue
            break
        latency = int((time.perf_counter() - t0) * 1000)

        if resp.status_code != 200:
            raise LLMError(self._DEEPSEEK_ERRORS.get(resp.status_code, f"DeepSeek API error {resp.status_code}"))
        try:
            data = resp.json()
            choice = data["choices"][0]
            text = choice["message"].get("content") or ""
            finish = choice.get("finish_reason")
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise LLMError("unexpected response from the DeepSeek API") from e

        usage = data.get("usage") or {}
        result_kwargs = dict(
            mode="live", model=self.settings.model, latency_ms=latency, stop_reason=finish,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        )
        self._log_usage(agent, {**result_kwargs, "provider": "deepseek"})
        if finish == "length":
            raise LLMError("output truncated at max_tokens")
        if finish == "content_filter":
            raise LLMError("model declined the request (content filter)")
        if not text.strip():
            raise LLMError("no structured output returned")
        try:
            parsed = output_model.model_validate_json(text.strip())
        except ValidationError as e:
            raise LLMError(f"LLM output failed schema validation: {e.error_count()} errors") from e
        return LLMResult(parsed=parsed, **result_kwargs)

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
