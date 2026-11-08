"""Every hand-written evaluation scenario must pass (mock mode + scripted LLM doubles)."""
import pytest

from core.config import Settings
from core.llm_client import LLMClient
from evaluation.checks import run_checks
from evaluation.run_eval import _agent_for
from evaluation.scenarios import all_scenarios

CASES = [(agent, sc) for agent, scs in all_scenarios().items() for sc in scs]


def test_at_least_ten_scenarios_per_agent():
    for agent, scs in all_scenarios().items():
        assert len(scs) >= 10, agent


@pytest.mark.parametrize("agent_key,sc", CASES, ids=[f"{a}-{s['id']}" for a, s in CASES])
def test_scenario(agent_key, sc):
    resp = _agent_for(agent_key, sc, LLMClient(Settings(mode="mock"))).run(sc["input"]).model_dump()
    failed = [c for c in run_checks(resp, sc["checks"]) if not c["passed"]]
    assert not failed, failed
