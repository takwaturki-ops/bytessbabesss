import pytest

from agents import FinancialAnalystAgent
from agents.financial_agent import unverified_numbers
from core import data
from core.llm_client import ScriptedLLMClient
from evaluation.reference_calc import reference_metrics


@pytest.fixture
def agent(mock_llm):
    return FinancialAnalystAgent(llm=mock_llm)


@pytest.mark.parametrize("split", ["dev", "eval", "all"])
def test_pandas_matches_independent_reference(agent, split):
    m = agent.run({"split": split}).data.metrics.model_dump()
    ref = reference_metrics(data.split_records("orders", split), data.split_records("transactions", split))
    for k, v in ref.items():
        assert m[k] == pytest.approx(v, abs=0.011), k


def test_breakdowns_sum_to_revenue(agent):
    m = agent.run({"split": "all"}).data.metrics
    for bd in (m.revenue_by_course, m.revenue_by_category, m.revenue_by_payment_method, m.revenue_by_month):
        assert sum(b.revenue_tnd for b in bd) == pytest.approx(m.gross_revenue_tnd, abs=0.05)
        assert sum(b.paid_orders for b in bd) == m.paid_orders


def test_mock_narrative_numbers_are_verified(agent):
    r = agent.run({"split": "dev"})
    assert r.meta.guardrails_triggered == []
    assert unverified_numbers(r.data.narrative, r.data.metrics) == []


def test_hallucinated_numbers_are_rejected():
    llm = ScriptedLLMClient(draft={"narrative": "We made 123456 TND and will grow 40%.", "insights": ["x"]})
    r = FinancialAnalystAgent(llm=llm).run({"split": "dev"})
    assert "123456" not in r.data.narrative
    assert r.meta.guardrails_triggered and r.meta.guardrails_triggered[0].startswith("unverified_numbers_replaced")


def test_bad_split_is_an_input_error(agent):
    assert agent.run({"split": "prod"}).status == "error"
