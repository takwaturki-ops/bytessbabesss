"""Hand-written evaluation scenarios (>= 10 per agent).

Categories: normal | edge | missing_input | invalid_output | ambiguous.
* `llm_draft` -> the scenario runs with a scripted LLM that returns this (possibly bad) draft, to prove guardrails.
* `llm_fail`  -> the scenario simulates an LLM outage, to prove deterministic fallback.
All data is SIMULATED.
"""
from __future__ import annotations

from core import data
from evaluation.reference_calc import reference_metrics


def C(path: str, op: str, value=None) -> dict:
    return {"path": path, "op": op, "value": value}


def S(sid, category, description, inp, checks, **extra) -> dict:
    return {"id": sid, "category": category, "description": description, "input": inp, "checks": checks, **extra}


OK = C("status", "eq", "ok")
ERR = C("status", "eq", "error")

# ----------------------------------------------------------------------------- payment
_PAY = {"transaction_id": "TXN-E1", "order_id": "ORD-E1", "status": "success", "amount_tnd": 199.0,
        "expected_amount_tnd": 199.0, "currency": "TND", "provider_reference": "PSIM-900001",
        "signature_valid": True, "payment_method": "card"}


def _p(**over):
    return {**_PAY, **over}


PAYMENT = [
    S("P01", "normal", "Success with full evidence", _p(),
      [OK, C("data.final_status", "eq", "success"), C("data.payment_confirmed", "eq", True),
       C("data.recommended_action", "eq", "grant_access")]),
    S("P02", "normal", "Card declined", _p(status="failed", provider_reference=None, failure_reason="card_declined"),
      [OK, C("data.final_status", "eq", "failed"), C("data.payment_confirmed", "eq", False),
       C("data.recommended_action", "eq", "retry_payment")]),
    S("P03", "normal", "Pending at provider", _p(status="pending", provider_reference=None),
      [OK, C("data.final_status", "eq", "pending"), C("data.recommended_action", "eq", "wait_for_confirmation")]),
    S("P04", "normal", "Provider flagged for review", _p(status="requires_review", provider_reference=None,
                                                          amount_tnd=99.5, failure_reason="amount_mismatch"),
      [OK, C("data.final_status", "eq", "requires_review"), C("data.recommended_action", "eq", "manual_review")]),
    S("P05", "edge", "Success claimed without provider reference", _p(provider_reference=None),
      [OK, C("data.final_status", "eq", "requires_review"), C("data.payment_confirmed", "eq", False),
       C("data.review_reasons", "contains", "missing_provider_reference")]),
    S("P06", "edge", "Success claimed with invalid signature", _p(signature_valid=False),
      [OK, C("data.final_status", "eq", "requires_review"),
       C("data.review_reasons", "contains", "signature_invalid_or_missing")]),
    S("P07", "edge", "Success with amount lower than expected", _p(amount_tnd=100.0),
      [OK, C("data.final_status", "eq", "requires_review"), C("data.review_reasons", "contains", "amount_mismatch")]),
    S("P08", "edge", "Success in wrong currency", _p(currency="EUR"),
      [OK, C("data.final_status", "eq", "requires_review"), C("data.review_reasons", "contains", "currency_not_tnd")]),
    S("P09", "ambiguous", "Provider alias 'authorized' means pending", _p(status="authorized", provider_reference=None),
      [OK, C("data.final_status", "eq", "pending")]),
    S("P10", "ambiguous", "Unknown provider status", _p(status="weird_state"),
      [OK, C("data.final_status", "eq", "requires_review"), C("data.payment_confirmed", "eq", False),
       C("data.review_reasons[0]", "startswith", "unknown_status")]),
    S("P11", "missing_input", "Missing order_id", {k: v for k, v in _PAY.items() if k != "order_id"},
      [ERR, C("errors", "contains", "invalid_input")]),
    S("P12", "missing_input", "Success but expected amount unknown", _p(expected_amount_tnd=None),
      [OK, C("data.final_status", "eq", "requires_review"),
       C("data.review_reasons", "contains", "amount_or_expected_amount_missing")]),
    S("P13", "invalid_output", "LLM claims success on a pending payment", _p(status="pending", provider_reference=None),
      [OK, C("data.final_status", "eq", "pending"), C("data.payment_confirmed", "eq", False),
       C("meta.guardrails_triggered", "contains", "unverified_success_claim_removed"),
       C("data.customer_message", "regex_absent", r"successful|confirmed|confirmé")],
      llm_draft={"summary": "Payment successful, access granted.", "customer_message": "Your payment was successful!"}),
    S("P14", "invalid_output", "LLM outage falls back to deterministic text", _p(),
      [OK, C("data.final_status", "eq", "success"), C("meta.mode", "eq", "fallback"),
       C("data.summary", "startswith", "[FALLBACK]")], llm_fail=True),
    S("P15", "ambiguous", "Upper-case alias PAID with full evidence", _p(status="PAID"),
      [OK, C("data.final_status", "eq", "success"), C("data.payment_confirmed", "eq", True)]),
    S("P16", "edge", "Zero amount on a pending event", _p(status="pending", amount_tnd=0.0, provider_reference=None),
      [OK, C("data.final_status", "eq", "requires_review"), C("data.review_reasons", "contains", "invalid_amount")]),
]

# ----------------------------------------------------------------------------- fraud
_EV = {"transaction_id": "T-1", "order_id": "O-1", "customer_id": "CUST0001", "course_id": "C002",
       "amount_tnd": 199.0, "expected_amount_tnd": 199.0, "currency": "TND", "status": "success",
       "signature_valid": True, "ip_country": "TN", "device_id": "DEV-0001-A", "card_fingerprint": "fp_a",
       "timestamp": "2026-10-01T10:00:00"}
_CTX = {"customer_id": "CUST0001", "home_country": "TN", "known_devices": ["DEV-0001-A"]}


def _e(**over):
    return {**_EV, **over}


def _fails(n, start_min=0, step=3, **over):
    return [_e(transaction_id=f"T-F{i}", status="failed", timestamp=f"2026-10-01T09:{start_min + i * step:02d}:00",
               **over) for i in range(n)]


def _f(event, history=None, ctx=None):
    return {"event": event, "history": history or [], "customer_context": ctx or _CTX}


FRAUD = [
    S("F01", "normal", "Single clean success", _f(_e()),
      [OK, C("data.action", "eq", "allow"), C("data.flags", "len_eq", 0), C("data.alert_summary", "is_null", True)]),
    S("F02", "normal", "Order already paid -> duplicate", _f(_e(transaction_id="T-2", timestamp="2026-10-01T10:05:00"),
                                                            [_e()]),
      [OK, C("data.action", "eq", "block"), C("data.flags", "contains", "DUPLICATE_PAYMENT")]),
    S("F03", "normal", "3 failed attempts in 10 min", _f(_e(status="pending"), _fails(3, 40)),
      [OK, C("data.action", "eq", "require_human_approval"), C("data.flags", "contains", "REPEATED_ATTEMPTS")]),
    S("F04", "normal", "6 failed attempts -> block", _f(_e(status="pending"), _fails(6, 40, 2)),
      [OK, C("data.action", "eq", "block"), C("data.flags", "contains", "REPEATED_ATTEMPTS")]),
    S("F05", "normal", "Amount differs from catalog", _f(_e(amount_tnd=99.5)),
      [OK, C("data.action", "eq", "require_human_approval"), C("data.flags", "contains", "AMOUNT_MISMATCH")]),
    S("F06", "normal", "Success with invalid provider signature", _f(_e(signature_valid=False)),
      [OK, C("data.action", "eq", "block"), C("data.flags", "contains", "INVALID_SIGNATURE")]),
    S("F07", "normal", "Foreign IP on unknown device", _f(_e(status="pending", ip_country="NG", device_id="DEV-NEW")),
      [OK, C("data.action", "eq", "require_human_approval"), C("data.flags", "contains", "GEO_MISMATCH")]),
    S("F08", "edge", "Foreign IP but known device (travelling customer)", _f(_e(ip_country="FR")),
      [OK, C("data.action", "eq", "allow")]),
    S("F09", "edge", "Two failures then success (false-positive check)", _f(_e(), _fails(2, 50)),
      [OK, C("data.action", "eq", "allow")]),
    S("F10", "edge", "Duplicate AND amount mismatch", _f(_e(transaction_id="T-2", amount_tnd=50.0,
                                                           timestamp="2026-10-01T10:05:00"), [_e()]),
      [OK, C("data.action", "eq", "block"), C("data.flags", "contains_all", ["DUPLICATE_PAYMENT", "AMOUNT_MISMATCH"]),
       C("data.risk_score", "gte", 90)]),
    S("F11", "missing_input", "Event without timestamp", _f({k: v for k, v in _EV.items() if k != "timestamp"}),
      [ERR, C("errors", "contains", "invalid_input")]),
    S("F12", "invalid_output", "LLM explanation tries to approve a blocked payment",
      _f(_e(signature_valid=False)),
      [OK, C("data.action", "eq", "block"), C("meta.guardrails_triggered", "contains", "contradictory_explanation_replaced"),
       C("data.explanation", "regex_absent", "safe to approve")],
      llm_draft={"explanation": "This transaction looks safe to approve.", "alert_summary": "ALLOW"}),
    S("F13", "edge", "Non-TND currency", _f(_e(currency="USD")),
      [OK, C("data.action", "eq", "require_human_approval"), C("data.flags", "contains", "CURRENCY_MISMATCH")]),
    S("F14", "edge", "Unusually high amount", _f(_e(amount_tnd=2000.0, expected_amount_tnd=2000.0)),
      [OK, C("data.action", "eq", "require_human_approval"), C("data.flags", "contains", "HIGH_AMOUNT")]),
    S("F15", "ambiguous", "Five failures but 2 hours ago (outside window)",
      _f(_e(), [_e(transaction_id=f"T-O{i}", status="failed", timestamp=f"2026-10-01T07:{i * 5:02d}:00")
                for i in range(5)]),
      [OK, C("data.action", "eq", "allow")]),
    S("F16", "edge", "Zero amount", _f(_e(status="pending", amount_tnd=0.0)),
      [OK, C("data.action", "eq", "block"), C("data.flags", "contains", "INVALID_AMOUNT")]),
]

# ----------------------------------------------------------------------------- financial
_ORDERS = [
    {"order_id": "O1", "course_id": "C001", "amount_tnd": 149.0, "list_price_tnd": 149.0, "payment_method": "card",
     "status": "paid", "created_at": "2026-09-05T10:00:00"},
    {"order_id": "O2", "course_id": "C002", "amount_tnd": 159.2, "list_price_tnd": 199.0,
     "payment_method": "mobile_wallet", "status": "paid", "created_at": "2026-09-10T10:00:00"},
    {"order_id": "O3", "course_id": "C003", "amount_tnd": 349.0, "list_price_tnd": 349.0, "payment_method": "card",
     "status": "failed", "created_at": "2026-09-12T10:00:00"},
    {"order_id": "O4", "course_id": "C005", "amount_tnd": 179.0, "list_price_tnd": 179.0, "payment_method": "card",
     "status": "pending", "created_at": "2026-10-01T10:00:00"},
    {"order_id": "O5", "course_id": "C001", "amount_tnd": 149.0, "list_price_tnd": 149.0, "payment_method": "card",
     "status": "paid", "created_at": "2026-10-03T10:00:00"},
    {"order_id": "O6", "course_id": "C009", "amount_tnd": 399.0, "list_price_tnd": 399.0,
     "payment_method": "bank_transfer", "status": "requires_review", "created_at": "2026-10-05T10:00:00"},
]


def _t(tid, oid, att, status, amt, reason=None):
    return {"transaction_id": tid, "order_id": oid, "attempt_no": att, "status": status, "amount_tnd": amt,
            "failure_reason": reason, "created_at": "2026-09-01T00:00:00"}


_TXNS = [_t("T1", "O1", 1, "success", 149.0), _t("T2", "O2", 1, "failed", 159.2, "insufficient_funds"),
         _t("T3", "O2", 2, "success", 159.2), _t("T4", "O3", 1, "failed", 349.0, "card_declined"),
         _t("T5", "O3", 2, "failed", 349.0, "card_declined"), _t("T6", "O4", 1, "pending", 179.0),
         _t("T7", "O5", 1, "success", 149.0), _t("T8", "O6", 1, "requires_review", 399.0)]
_INLINE = {"orders": _ORDERS, "transactions": _TXNS}


def _split_checks(split: str) -> list[dict]:
    ref = reference_metrics(data.split_records("orders", split), data.split_records("transactions", split))
    return [OK] + [C(f"data.metrics.{k}", "eq", float(v) if isinstance(v, float) else v) for k, v in ref.items()]


def financial_scenarios() -> list[dict]:
    return [
        S("FA01", "normal", "Overview on a known mini-dataset", {**_INLINE, "question": "Overview please"},
          [OK, C("data.metrics.gross_revenue_tnd", "eq", 457.2), C("data.metrics.paid_orders", "eq", 3),
           C("data.metrics.total_orders", "eq", 6)]),
        S("FA02", "normal", "Average order value and discount total", {**_INLINE, "question": "What is our AOV?"},
          [OK, C("data.metrics.average_order_value_tnd", "eq", 152.4), C("data.metrics.discount_total_tnd", "eq", 39.8)]),
        S("FA03", "normal", "Payment statistics", {**_INLINE, "question": "How reliable are payments?"},
          [OK, C("data.metrics.payment_success_rate", "eq", 0.375),
           C("data.metrics.first_attempt_success_rate", "eq", 0.3333), C("data.metrics.order_conversion_rate", "eq", 0.5)]),
        S("FA04", "normal", "Best-selling course", {**_INLINE, "question": "Which course sells best?"},
          [OK, C("data.metrics.revenue_by_course[0].key", "eq", "C001"),
           C("data.metrics.revenue_by_course[0].revenue_tnd", "eq", 298.0)]),
        S("FA05", "edge", "Date filter on October only",
          {**_INLINE, "question": "October revenue?", "date_from": "2026-10-01", "date_to": "2026-10-31"},
          [OK, C("data.metrics.total_orders", "eq", 3), C("data.metrics.gross_revenue_tnd", "eq", 149.0),
           C("data.metrics.paid_orders", "eq", 1)]),
        S("FA06", "edge", "Empty dataset", {"orders": [], "transactions": [], "question": "Overview"},
          [OK, C("data.metrics.total_orders", "eq", 0), C("data.metrics.gross_revenue_tnd", "eq", 0.0),
           C("data.metrics.average_order_value_tnd", "eq", 0.0), C("data.metrics.payment_success_rate", "eq", 0.0)]),
        S("FA07", "missing_input", "Orders missing required column",
          {"orders": [{"order_id": "X", "status": "paid"}], "transactions": [], "question": "Overview"},
          [ERR, C("errors[0]", "regex_present", "missing columns")]),
        S("FA08", "invalid_output", "LLM invents a revenue figure", {**_INLINE, "question": "Overview"},
          [OK, C("data.narrative", "regex_absent", "999999"),
           C("meta.guardrails_triggered[0]", "startswith", "unverified_numbers_replaced")],
          llm_draft={"narrative": "Revenue reached 999999 TND this month.", "insights": ["Growth is 300%."]}),
        S("FA09", "normal", "Dev split matches independent calculation", {"split": "dev", "question": "Overview"},
          _split_checks("dev")),
        S("FA10", "normal", "Eval split matches independent calculation", {"split": "eval", "question": "Overview"},
          _split_checks("eval")),
        S("FA11", "normal", "Failure reasons breakdown", {**_INLINE, "question": "Why do payments fail?"},
          [OK, C("data.metrics.failure_reasons.card_declined", "eq", 2),
           C("data.metrics.failure_reasons.insufficient_funds", "eq", 1)]),
        S("FA12", "invalid_output", "Valid LLM narrative is kept (no false guardrail)",
          {**_INLINE, "question": "Overview"},
          [OK, C("meta.guardrails_triggered", "len_eq", 0), C("data.narrative", "regex_present", "457.2")],
          llm_draft={"narrative": "Revenue was 457.2 TND from 3 paid orders; conversion is 50%.",
                     "insights": ["Payment success rate is 37.5%."]}),
        S("FA13", "ambiguous", "Date range with no data",
          {**_INLINE, "question": "December?", "date_from": "2026-12-01", "date_to": "2026-12-31"},
          [OK, C("data.metrics.total_orders", "eq", 0), C("data.metrics.gross_revenue_tnd", "eq", 0.0)]),
    ]


# ----------------------------------------------------------------------------- sales
_STUDENT = {"segment": "student", "experience_level": "beginner", "interests": ["programming"], "budget_max_tnd": 250}
_GROUNDED = C("data.catalog_grounded", "eq", True)

SALES = [
    S("S01", "normal", "Purchase intent (EN)", {"customer_message": "I want to enroll in Python for AI, how can I pay?"},
      [OK, C("data.detected_intent", "eq", "purchase_intent"), C("data.next_action", "eq", "send_payment_link"),
       C("data.recommended_courses[*].course_id", "contains", "C002"), C("data.reply", "regex_present", r"199"),
       _GROUNDED]),
    S("S02", "normal", "Information request", {"customer_message": "Do you have a machine learning course? How long is it?"},
      [OK, C("data.detected_intent", "eq", "information_request"),
       C("data.recommended_courses[*].course_id", "contains_any", ["C003"])]),
    S("S03", "normal", "Price objection from a student",
      {"customer_message": "Deep Learning with PyTorch is too expensive for me.", "customer_profile": _STUDENT},
      [OK, C("data.detected_intent", "eq", "price_objection"), C("data.objection_type", "eq", "price"),
       C("data.next_action", "eq", "handle_objection"), _GROUNDED]),
    S("S04", "normal", "Course comparison",
      {"customer_message": "What's the difference between Machine Learning Essentials and Deep Learning with PyTorch?"},
      [OK, C("data.detected_intent", "eq", "course_comparison"),
       C("data.recommended_courses[*].course_id", "contains_all", ["C003", "C004"])]),
    S("S05", "normal", "Payment issue is routed, no upsell",
      {"customer_message": "My card was declined when paying for Generative AI & Prompt Engineering."},
      [OK, C("data.detected_intent", "eq", "payment_issue"), C("data.next_action", "eq", "route_to_payment_support"),
       C("data.recommended_courses", "len_eq", 0)]),
    S("S06", "normal", "Support request", {"customer_message": "I can't log in to my course."},
      [OK, C("data.detected_intent", "eq", "support_request"), C("data.next_action", "eq", "route_to_customer_support")]),
    S("S07", "normal", "Not interested", {"customer_message": "Thanks but I'm not interested anymore."},
      [OK, C("data.detected_intent", "eq", "not_interested"), C("data.next_action", "eq", "end_conversation")]),
    S("S08", "normal", "Purchase intent (FR)",
      {"customer_message": "Je veux m'inscrire à la formation AI in FinTech. Comment payer ?"},
      [OK, C("data.detected_intent", "eq", "purchase_intent"),
       C("data.recommended_courses[*].course_id", "contains", "C009")]),
    S("S09", "normal", "Information request (darija)",
      {"customer_message": "3andkom formation fi marketing? 9addech todhher?"},
      [OK, C("data.detected_intent", "eq", "information_request"),
       C("data.recommended_courses[*].course_id", "contains", "C008")]),
    S("S10", "edge", "Difficulty objection -> beginner course",
      {"customer_message": "I'm interested in data analysis but I'm not sure I have the level, I've never coded."},
      [OK, C("data.objection_type", "eq", "difficulty"),
       C("data.recommended_courses[*].level", "subset", ["beginner"]), C("data.recommended_courses", "len_gte", 1)]),
    S("S11", "missing_input", "Empty message", {"customer_message": ""}, [ERR, C("errors", "contains", "invalid_input")]),
    S("S12", "invalid_output", "LLM hallucinates a price and a course",
      {"customer_message": "How much is Python for AI?"},
      [OK, C("data.catalog_grounded", "eq", False), C("data.reply", "regex_absent", r"(?<!\d)99 TND"),
       C("data.recommended_courses[*].course_id", "not_contains", "C999"),
       C("meta.guardrails_triggered", "len_gte", 1)],
      llm_draft={"reply": "Python for AI costs only 99 TND today!", "detected_intent": "information_request",
                 "objection_type": "none", "recommended_course_ids": ["C002", "C999"],
                 "recommendation_reasons": ["cheap", "new"], "next_action": "present_courses",
                 "purchase_intent_score": 0.5, "confidence": 0.9}),
    S("S13", "invalid_output", "LLM claims payment is done", {"customer_message": "I want to buy Python for AI"},
      [OK, C("data.reply", "regex_absent", "payment (is|was) confirmed"), C("data.catalog_grounded", "eq", False)],
      llm_draft={"reply": "Great news, your payment is confirmed for Python for AI (199 TND)!",
                 "detected_intent": "purchase_intent", "objection_type": "none", "recommended_course_ids": ["C002"],
                 "recommendation_reasons": ["requested"], "next_action": "send_payment_link",
                 "purchase_intent_score": 0.9, "confidence": 0.9}),
    S("S14", "ambiguous", "Bare greeting", {"customer_message": "Hello"},
      [OK, C("data.detected_intent", "eq", "information_request"),
       C("data.next_action", "in", ["present_courses", "answer_question"])]),
    S("S15", "edge", "Unknown customer id still answers", {"customer_message": "Do you have Python courses?",
                                                           "customer_id": "CUST9999"},
      [OK, C("meta.warnings", "contains", "unknown_customer_id:CUST9999")]),
]

# ----------------------------------------------------------------------------- customer intel


def _conv(*texts):
    return {"turns": [{"role": "customer" if i % 2 == 0 else "agent", "text": t} for i, t in enumerate(texts)]}


_AG = "Here are the details of the course."
INTEL = [
    S("I01", "normal", "Happy buyer", _conv("I want to enroll in Python for AI. How can I pay?",
                                            "Python for AI costs 199 TND.", "Great, that sounds perfect, thank you!"),
      [OK, C("data.primary_intent", "eq", "purchase_intent"), C("data.sentiment", "eq", "positive"),
       C("data.purchase_stage", "eq", "decision"), C("data.interest_score", "gte", 80),
       C("data.mentioned_course_ids", "contains", "C002")]),
    S("I02", "normal", "Price objection, disappointed (FR)",
      _conv("La formation Deep Learning with PyTorch m'intéresse mais c'est trop cher.", _AG,
            "Je suis déçu, ce n'est pas normal."),
      [OK, C("data.primary_intent", "eq", "price_objection"), C("data.objections", "contains", "price"),
       C("data.sentiment", "eq", "negative")]),
    S("I03", "normal", "Time objection, undecided",
      _conv("Can you tell me more about your python courses?", _AG, "I work full time, I don't have much time.", _AG,
            "OK, I'll think about it."),
      [OK, C("data.primary_intent", "eq", "information_request"), C("data.objections", "contains", "time"),
       C("data.sentiment", "eq", "neutral")]),
    S("I04", "normal", "Trust objection",
      _conv("Do you have something about fintech?", _AG, "Is the certificate recognized? I've never heard of you before.",
            _AG, "OK, I'll think about it."),
      [OK, C("data.objections", "contains", "trust")]),
    S("I05", "normal", "Payment problem",
      _conv("I tried to pay for Python for AI but my card was declined.", _AG, "This is frustrating, I expected better."),
      [OK, C("data.primary_intent", "eq", "payment_issue"), C("data.purchase_stage", "eq", "support"),
       C("data.sentiment", "eq", "negative")]),
    S("I06", "normal", "Lost lead", _conv("Thanks but I'm not interested anymore.", "OK, thank you."),
      [OK, C("data.primary_intent", "eq", "not_interested"), C("data.purchase_stage", "eq", "lost"),
       C("data.interest_score", "lte", 20)]),
    S("I07", "normal", "Support request",
      _conv("I can't log in to my Data Analysis with AI course.", _AG, "OK, I'll think about it."),
      [OK, C("data.primary_intent", "eq", "support_request"), C("data.mentioned_course_ids", "contains", "C007")]),
    S("I08", "normal", "Darija happy buyer",
      _conv("N7eb nechri formation AI for Marketing & Sales, kifech nkhallas?", _AG, "Ya3tik essa7a, behi barcha!"),
      [OK, C("data.primary_intent", "eq", "purchase_intent"), C("data.sentiment", "eq", "positive"),
       C("data.mentioned_course_ids", "contains", "C008")]),
    S("I09", "edge", "Multiple objections",
      _conv("Avez-vous une formation sur machine learning ?", _AG, "C'est trop cher pour moi.", _AG,
            "J'ai peur que ce soit trop difficile."),
      [OK, C("data.objections", "contains_all", ["price", "difficulty"])]),
    S("I10", "missing_input", "No turns", {"turns": []}, [ERR, C("errors", "contains", "invalid_input")]),
    S("I11", "missing_input", "Only agent turns", {"turns": [{"role": "agent", "text": "Hello!"}]},
      [ERR, C("errors", "contains", "invalid_input")]),
    S("I12", "invalid_output", "LLM returns unknown course and out-of-range score",
      _conv("Tell me about AI Foundations for Everyone"),
      [OK, C("data.mentioned_course_ids", "eq", ["C001"]), C("data.interest_score", "eq", 100),
       C("meta.guardrails_triggered", "contains_all", ["unknown_course_id_removed", "scores_clamped"])],
      llm_draft={"primary_intent": "information_request", "needs": ["learn AI"], "motivations": [], "objections": [],
                 "sentiment": "positive", "sentiment_score": 0.5, "interest_score": 150, "satisfaction_score": 70,
                 "purchase_stage": "awareness", "mentioned_course_ids": ["C001", "C777"],
                 "recommended_follow_up": "Send syllabus", "summary": "Curious lead.", "confidence": 0.8}),
    S("I13", "invalid_output", "LLM outage -> heuristic fallback", _conv("I want to buy Python for AI"),
      [OK, C("meta.mode", "eq", "fallback"), C("data.summary", "startswith", "[FALLBACK]"),
       C("data.primary_intent", "eq", "purchase_intent")], llm_fail=True),
    S("I14", "ambiguous", "Mixed signals",
      _conv("Great course list but the price is too much.", _AG, "OK, I'll think about it."),
      [OK, C("data.sentiment", "eq", "neutral"), C("data.objections", "contains", "price")]),
]


def all_scenarios() -> dict[str, list[dict]]:
    return {"sales": SALES, "customer_intel": INTEL, "payment": PAYMENT, "financial": financial_scenarios(),
            "fraud": FRAUD}
