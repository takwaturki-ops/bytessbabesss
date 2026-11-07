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


@dataclass(frozen=True)
class Settings:
    mode: str = "mock"              # "mock" (no API calls) | "live" (real Claude calls)
    model: str = DEFAULT_MODEL
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
        model = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip()
        model = MODEL_ALIASES.get(model.lower(), model)
        return cls(
            mode=mode,
            model=model,
            effort=os.getenv("LLM_EFFORT", "low").strip().lower(),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1500")),
            timeout_s=float(os.getenv("LLM_TIMEOUT_S", "45")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
        )
