import os

# Tests never call the real API: force mock mode before any project module reads the environment.
os.environ["LLM_MODE"] = "mock"

import pytest  # noqa: E402

from core.config import Settings  # noqa: E402
from core.llm_client import LLMClient  # noqa: E402


@pytest.fixture
def mock_llm() -> LLMClient:
    return LLMClient(Settings(mode="mock"))
