"""Customer Intelligence Agent: structured insights from a conversation."""
from __future__ import annotations

from core import data
from core.base_agent import BaseAgent
from schemas.common import AgentMeta
from schemas.intel import CustomerInsights, IntelDraft, IntelInput
from tools.catalog_search import mentioned_course_ids
from tools.text_rules import detect_intent, detect_objections, has, norm, sentiment_label, sentiment_score

BASE_INTEREST = {"purchase_intent": 85, "course_comparison": 70, "information_request": 60, "price_objection": 55,
                 "payment_issue": 75, "support_request": 50, "not_interested": 10}
SATISFACTION = {"positive": 80, "neutral": 60, "negative": 30}
STAGE = {"purchase_intent": "decision", "course_comparison": "consideration", "information_request": "awareness",
         "price_objection": "consideration", "payment_issue": "support", "support_request": "support",
         "not_interested": "lost"}
FOLLOW_UP = {
    "purchase_intent": "Send the payment link and confirm enrolment details.",
    "course_comparison": "Send a side-by-side comparison and suggest a short call.",
    "information_request": "Share the course syllabus and a beginner-friendly recommendation.",
    "price_objection": "Offer an applicable discount code or a more affordable course.",
    "payment_issue": "Escalate to payment support and check the transaction status.",
    "support_request": "Escalate to customer support to restore course access.",
    "not_interested": "Stop outreach; add to a low-frequency newsletter only if consented.",
}
MOTIVATION_KW = {
    "career growth": ("career", "job", "emploi", "carrière", "promotion", "salary"),
    "grow a business": ("business", "company", "entreprise", "clients", "startup", "sales"),
    "academic success": ("student", "étudiant", "exam", "university", "fac"),
    "productivity": ("productivity", "productivité", "faster", "automate"),
}


def heuristic_insights(inp: IntelInput) -> IntelDraft:
    cust = [t.text for t in inp.turns if t.role == "customer"]
    all_text = " ".join(t.text for t in inp.turns)
    intent = detect_intent(cust[0])
    objections: list[str] = []
    for text in cust:
        for o in detect_objections(text):
            if o not in objections:
                objections.append(o)
    if intent == "price_objection" and "price" not in objections:
        objections.insert(0, "price")
    score = sentiment_score(cust)
    sent = sentiment_label(score)
    interest = BASE_INTEREST[intent] + {"positive": 5, "neutral": 0, "negative": -10}[sent]
    ids = mentioned_course_ids(all_text)
    cmap = data.course_map()
    needs = [f"learn {cmap[i]['category'].replace('_', ' ')} ({cmap[i]['title']})" for i in ids][:3]
    if intent == "payment_issue":
        needs.append("resolve a payment problem")
    if intent == "support_request":
        needs.append("regain access to purchased course")
    t = norm(" ".join(cust))
    motivations = [m for m, kws in MOTIVATION_KW.items() if any(has(t, k) for k in kws)]
    stage = STAGE[intent]
    if intent == "purchase_intent" and sent != "positive":
        stage = "consideration"
    return IntelDraft(
        primary_intent=intent, needs=needs, motivations=motivations, objections=objections, sentiment=sent,
        sentiment_score=score, interest_score=max(0, min(100, interest)), satisfaction_score=SATISFACTION[sent],
        purchase_stage=stage, mentioned_course_ids=ids, recommended_follow_up=FOLLOW_UP[intent],
        summary=f"Customer intent: {intent.replace('_', ' ')}; sentiment {sent}; "
                f"objections: {', '.join(objections) or 'none'}.",
        confidence=0.55,
    )


class CustomerIntelAgent(BaseAgent[IntelInput, CustomerInsights]):
    name = "customer_intel_agent"
    input_model = IntelInput
    output_model = CustomerInsights
    prompt_name = "customer_intel"
    max_tokens = 1200

    def process(self, inp: IntelInput, meta: AgentMeta) -> CustomerInsights:
        hints = heuristic_insights(inp)
        payload = {
            "turns": [t.model_dump() for t in inp.turns[-20:]],   # cap context: last 20 turns
            "catalog_index": {c["course_id"]: c["title"] for c in data.courses()},
            "rule_hints": {"intent": hints.primary_intent, "objections": hints.objections,
                           "sentiment_score": hints.sentiment_score},
        }
        draft = self.draft(payload=payload, draft_model=IntelDraft, mock=lambda: hints, meta=meta,
                           text_fields=IntelDraft.text_fields)
        meta.decision_source = "llm" if meta.llm_used else "deterministic"

        # Guardrails: catalog IDs only, clamp numeric ranges, dedupe lists.
        cmap = data.course_map()
        ids = [i for i in dict.fromkeys(draft.mentioned_course_ids) if i in cmap]
        if len(ids) != len(set(draft.mentioned_course_ids)):
            meta.guardrails_triggered.append("unknown_course_id_removed")
        clamp = lambda v, lo, hi: max(lo, min(hi, v))  # noqa: E731
        if not (-1 <= draft.sentiment_score <= 1 and 0 <= draft.interest_score <= 100
                and 0 <= draft.satisfaction_score <= 100 and 0 <= draft.confidence <= 1):
            meta.guardrails_triggered.append("scores_clamped")
        return CustomerInsights(
            conversation_id=inp.conversation_id, customer_id=inp.customer_id, primary_intent=draft.primary_intent,
            needs=draft.needs[:6], motivations=draft.motivations[:6], objections=list(dict.fromkeys(draft.objections)),
            sentiment=draft.sentiment, sentiment_score=clamp(draft.sentiment_score, -1.0, 1.0),
            interest_score=int(clamp(draft.interest_score, 0, 100)),
            satisfaction_score=int(clamp(draft.satisfaction_score, 0, 100)), purchase_stage=draft.purchase_stage,
            mentioned_course_ids=ids, recommended_follow_up=draft.recommended_follow_up, summary=draft.summary,
            confidence=clamp(draft.confidence, 0.0, 1.0),
        )
