import sys

import pytest

from agents import AGENTS, PaymentAgent
from core.config import Settings
from core.llm_client import LLMClient, ScriptedLLMClient


def test_default_settings_are_mock_and_sonnet(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    s = Settings.from_env()
    assert s.mode == "mock"
    assert s.model == "claude-sonnet-5-5"


@pytest.mark.parametrize("alias,model", [("haiku", "claude-haiku-5-5"), ("opus", "claude-opus-5-5"),
                                         ("sonnet", "claude-sonnet-5-5"), ("claude-opus-5-5", "claude-opus-5-5")])
def test_model_aliases(monkeypatch, alias, model):
    monkeypatch.setenv("LLM_MODEL", alias)
    assert Settings.from_env().model == model


def test_invalid_mode_rejected(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "production")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_every_agent_has_uniform_interface(mock_llm):
    for cls in AGENTS.values():
        agent = cls(llm=mock_llm)
        assert agent.system_prompt  # prompt file loaded
        resp = agent.run({})  # empty input must not crash
        assert resp.status in ("ok", "error")
        assert resp.meta.agent == agent.name
        assert resp.meta.data_source == "simulated"


def test_mock_mode_makes_no_api_call_and_is_labelled(mock_llm):
    resp = PaymentAgent(llm=mock_llm).run({"transaction_id": "T", "order_id": "O", "status": "pending"})
    assert resp.meta.mode == "mock" and resp.meta.llm_used is False and resp.meta.llm_calls == 0
    assert resp.data.summary.startswith("[MOCK]")


def test_mock_mode_does_not_import_anthropic(mock_llm):
    sys.modules.pop("anthropic", None)
    PaymentAgent(llm=mock_llm).run({"transaction_id": "T", "order_id": "O", "status": "failed"})
    assert "anthropic" not in sys.modules


def test_schema_invalid_llm_output_falls_back():
    llm = ScriptedLLMClient(draft={"summary": 123})  # missing customer_message, wrong type
    resp = PaymentAgent(llm=llm).run({"transaction_id": "T", "order_id": "O", "status": "pending"})
    assert resp.status == "ok"
    assert resp.meta.mode == "fallback"
    assert any("schema validation" in w for w in resp.meta.warnings)


def test_live_mode_without_key_degrades_gracefully(monkeypatch):
    """Live mode with no credentials must not crash the agent: it falls back and says so."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")  # unreachable: no network traffic leaves the machine
    llm = LLMClient(Settings(mode="live", timeout_s=2, max_retries=0))
    resp = PaymentAgent(llm=llm).run({"transaction_id": "T", "order_id": "O", "status": "failed"})
    assert resp.status == "ok" and resp.data.final_status == "failed"
    assert resp.meta.mode == "fallback"
