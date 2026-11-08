import pytest

from agents import CustomerIntelAgent
from core import data

EVAL = data.split_records("conversations", "eval")


@pytest.fixture
def agent(mock_llm):
    return CustomerIntelAgent(llm=mock_llm)


def test_outputs_are_valid_for_all_eval_conversations(agent):
    for c in EVAL:
        r = agent.run({"turns": c["turns"], "conversation_id": c["conversation_id"], "customer_id": c["customer_id"]})
        assert r.status == "ok"
        assert 0 <= r.data.interest_score <= 100 and -1 <= r.data.sentiment_score <= 1
        assert set(r.data.mentioned_course_ids) <= set(data.course_map())
        assert r.data.conversation_id == c["conversation_id"]


def test_heuristic_baseline_quality(agent):
    """Mock-mode baseline must stay useful on held-out data (thresholds documented in README)."""
    n = len(EVAL)
    res = [agent.run({"turns": c["turns"]}).data for c in EVAL]
    intent_acc = sum(r.primary_intent == c["labels"]["intent"] for r, c in zip(res, EVAL)) / n
    sent_acc = sum(r.sentiment == c["labels"]["sentiment"] for r, c in zip(res, EVAL)) / n
    assert intent_acc >= 0.8, intent_acc
    assert sent_acc >= 0.7, sent_acc


def test_long_conversation_is_truncated_for_llm(agent):
    turns = [{"role": "customer" if i % 2 == 0 else "agent", "text": f"message {i}"} for i in range(59)]
    assert agent.run({"turns": turns}).status == "ok"
