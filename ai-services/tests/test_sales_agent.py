import pytest

from agents import SalesAgent
from core import data
from tools.catalog_search import allowed_prices, prices_in_text


@pytest.fixture
def agent(mock_llm):
    return SalesAgent(llm=mock_llm)


def test_recommendations_use_catalog_prices(agent):
    cmap = data.course_map()
    r = agent.run({"customer_message": "I want to learn machine learning", "customer_id": "CUST0001"})
    assert r.status == "ok" and r.data.recommended_courses
    for rec in r.data.recommended_courses:
        assert rec.price_tnd == cmap[rec.course_id]["price_tnd"]


def test_every_reply_on_eval_conversations_is_grounded(agent):
    allowed = allowed_prices()
    for c in data.split_records("conversations", "eval"):
        r = agent.run({"customer_message": c["turns"][0]["text"], "customer_id": c["customer_id"]})
        assert r.status == "ok"
        assert all(round(p, 2) in allowed for p in prices_in_text(r.data.reply)), r.data.reply
        assert r.data.catalog_grounded


def test_history_is_used_for_context(agent):
    r = agent.run({"customer_message": "How much is it?",
                   "conversation_history": [{"role": "customer", "text": "Tell me about Computer Vision Bootcamp"}]})
    assert "C010" in [x.course_id for x in r.data.recommended_courses]


def test_no_course_pushed_on_payment_issue(agent):
    r = agent.run({"customer_message": "My payment failed for Python for AI"})
    assert r.data.detected_intent == "payment_issue" and r.data.recommended_courses == []


def test_mock_reply_is_labelled(agent):
    r = agent.run({"customer_message": "Hello"})
    assert r.data.reply.startswith("[MOCK]") and r.meta.mode == "mock"
