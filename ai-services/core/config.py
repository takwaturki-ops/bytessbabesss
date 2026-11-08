"""Central configuration, read from environment / .env (python-dotenv)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:  # .env is optional; python-dotenv is a declared dependency
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:  # pragma: no cover
    pass

MODEL_ALIASES = {
    "sonnet": "claude-sonnet-5-5",   # default: balance of quality and cost
    "haiku": "claude-haiku-5-5",     # cheapest option
    "opus": "claude-opus-5-5",       # optional quality upgrade
}
DEFAULT_MODEL = MODEL_ALIASES["sonnet"]

# Live-mode providers. "anthropic" (Claude) is the default and the one the evaluation suite was run with.
PROVIDERS = ("anthropic", "deepseek")
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"


def resolve_model(provider: str, raw: str | None) -> str:
    """Model id for a provider. Claude aliases/ids left in .env fall back to the provider's default model."""
    value = (raw or "").strip()
    if provider == "deepseek":
        if not value or value.lower() in MODEL_ALIASES or value.lower().startswith("claude"):
            return DEEPSEEK_DEFAULT_MODEL
        return value
    if not value:
        return DEFAULT_MODEL
    return MODEL_ALIASES.get(value.lower(), value)


@dataclass(frozen=True)
class Settings:
    mode: str = "mock"              # "mock" (no API calls) | "live" (real LLM calls)
    provider: str = "anthropic"     # live mode only: "anthropic" (Claude) | "deepseek"
    model: str = DEFAULT_MODEL
    base_url: str | None = None     # deepseek only (default https://api.deepseek.com)
    effort: str = "low"             # low | medium | high - low keeps cost/latency down
    max_tokens: int = 1500          # hard cap per call (includes thinking tokens)
    timeout_s: float = 45.0
    max_retries: int = 2
    usage_log: Path = ROOT / "logs" / "llm_usage.jsonl"

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("LLM_MODE", "mock").strip().lower()
        if mode not in ("mock", "live"):
            raise ValueError(f"LLM_MODE must be 'mock' or 'live', got {mode!r}")
        provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower() or "anthropic"
        if provider not in PROVIDERS:
            raise ValueError(f"LLM_PROVIDER must be one of {PROVIDERS}, got {provider!r}")
        return cls(
            mode=mode,
            provider=provider,
            model=resolve_model(provider, os.getenv("LLM_MODEL")),
            base_url=(os.getenv("DEEPSEEK_BASE_URL") or DEEPSEEK_DEFAULT_BASE_URL) if provider == "deepseek" else None,
            effort=os.getenv("LLM_EFFORT", "low").strip().lower(),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1500")),
            timeout_s=float(os.getenv("LLM_TIMEOUT_S", "45")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
        )
