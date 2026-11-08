"""DeepSeek provider tests. A fake HTTP transport stands in for the API: no network, no credits."""
import json

import httpx
import pytest
from pydantic import BaseModel

from agents import PaymentAgent
from core.config import Settings, resolve_model
from core.llm_client import LLMClient, LLMError


class Reply(BaseModel):
    message: str
    score: float


def deepseek_settings(**overrides) -> Settings:
    base = dict(mode="live", provider="deepseek", model="deepseek-chat",
                base_url="https://api.deepseek.test", timeout_s=2, max_retries=0)
    return Settings(**{**base, **overrides})


def client_with(handler, **settings) -> LLMClient:
    http = httpx.Client(base_url="https://api.deepseek.test", transport=httpx.MockTransport(handler))
    return LLMClient(deepseek_settings(**settings), http_client=http)


def completion(content: str, finish: str = "stop", status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30},
    })


def generate(llm: LLMClient):
    return llm.generate(agent="test", system="You are a test agent.", payload={"q": "bonjour"},
                        output_model=Reply, mock=lambda: Reply(message="mock", score=0))


@pytest.fixture(autouse=True)
def deepseek_key(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.setattr("core.llm_client.LLMClient._log_usage", lambda self, agent, info: None)  # keep the real usage log clean


def test_valid_json_is_parsed_and_labelled_live():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return completion('{"message": "Ahla! Voici le cours.", "score": 0.8}')

    result = generate(client_with(handler))
    assert result.mode == "live" and result.model == "deepseek-chat"
    assert result.parsed == Reply(message="Ahla! Voici le cours.", score=0.8)
    assert (result.input_tokens, result.output_tokens) == (120, 30)

    assert seen["url"] == "https://api.deepseek.test/chat/completions"
    assert seen["auth"] == "Bearer sk-test-not-a-real-key"
    body = seen["body"]
    assert body["model"] == "deepseek-chat"
    assert body["response_format"] == {"type": "json_object"}
    system = body["messages"][0]["content"]
    assert "json" in system and '"score"' in system, "JSON mode needs the word json and the schema in the prompt"
    assert json.loads(body["messages"][1]["content"]) == {"q": "bonjour"}


@pytest.mark.parametrize("content", [
    '{"message": "ok"}',                 # missing field
    '{"message": "ok", "score": "high"}',  # wrong type
    "Bien sûr ! Voici ma réponse.",      # not JSON
    "",                                  # empty content (DeepSeek JSON mode can return this)
])
def test_unusable_output_raises(content):
    with pytest.raises(LLMError):
        generate(client_with(lambda r: completion(content)))


def test_truncated_output_raises():
    with pytest.raises(LLMError, match="truncated"):
        generate(client_with(lambda r: completion('{"message": "o', finish="length")))


@pytest.mark.parametrize("status, message", [(401, "authentication"), (402, "balance"), (429, "rate limited")])
def test_api_errors_are_explained(status, message):
    with pytest.raises(LLMError, match=message):
        generate(client_with(lambda r: httpx.Response(status, json={"error": {"message": "x"}})))


def test_retries_transient_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr("core.llm_client.time.sleep", lambda s: None)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else completion('{"message": "ok", "score": 1}')

    result = generate(client_with(handler, max_retries=1))
    assert result.parsed.message == "ok" and calls["n"] == 2


def test_missing_key_raises_without_any_request(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    def handler(request):
        raise AssertionError("no request may be sent without a key")

    with pytest.raises(LLMError, match="DEEPSEEK_API_KEY"):
        generate(client_with(handler))


def test_agent_falls_back_when_deepseek_fails():
    """A failing provider never breaks an agent: deterministic fallback, decisions unchanged."""
    llm = client_with(lambda r: httpx.Response(500))
    resp = PaymentAgent(llm=llm).run({"transaction_id": "T", "order_id": "O", "status": "failed"})
    assert resp.status == "ok" and resp.data.final_status == "failed"
    assert resp.meta.mode == "fallback"


def test_provider_settings_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_MODEL", "sonnet")  # Claude alias left in .env
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    s = Settings.from_env()
    assert (s.provider, s.model, s.base_url) == ("deepseek", "deepseek-chat", "https://api.deepseek.com")

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_resolve_model():
    assert resolve_model("deepseek", "deepseek-reasoner") == "deepseek-reasoner"
    assert resolve_model("deepseek", "claude-sonnet-5-5") == "deepseek-chat"
    assert resolve_model("anthropic", "haiku") == "claude-haiku-5-5"
    assert resolve_model("anthropic", None) == "claude-sonnet-5-5"
