import os

# Tests never call the real API: force mock mode before any project module reads the environment.
os.environ["LLM_MODE"] = "mock"
# Same for the provider and model: the developer's .env (e.g. LLM_PROVIDER=deepseek) must not change test results.
os.environ["LLM_PROVIDER"] = "anthropic"
os.environ["LLM_MODEL"] = ""  # empty (not removed) so python-dotenv does not load the .env value; "" = default model

import pytest  # noqa: E402

from core.config import Settings  # noqa: E402
from core.llm_client import LLMClient  # noqa: E402


@pytest.fixture
def mock_llm() -> LLMClient:
    return LLMClient(Settings(mode="mock"))
