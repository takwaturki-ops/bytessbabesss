"""Voice Sales Agent (text first). Grounded on the SIMULATED catalog; prices are verified after generation."""
from __future__ import annotations

from agents.payment_agent import SUCCESS_CLAIM
from core import data
from core.base_agent import FALLBACK_PREFIX, BaseAgent
from data_generation.catalog import DISCOUNT_CODES
from schemas.common import AgentMeta
from schemas.sales import CourseRecommendation, SalesDraft, SalesInput, SalesOutput
from tools.catalog_search import allowed_prices, mentioned_course_ids, prices_in_text, search_courses
from tools.text_rules import detect_intent, detect_objections

INTENT_SCORE = {"purchase_intent": 0.85, "course_comparison": 0.6, "price_objection": 0.55,
                "information_request": 0.5, "payment_issue": 0.6, "support_request": 0.3, "not_interested": 0.05}
NO_RECO_INTENTS = {"payment_issue", "support_request", "not_interested"}


def _fmt(c: dict) -> str:
    return f"{c['title']} ({c['price_tnd']:.0f} TND, {c['duration_weeks']} weeks, {c['level']})"


def template_draft(intent: str, objections: list[str], candidates: list[dict], profile: dict) -> SalesDraft:
    """Deterministic reply built only from catalog facts (mock mode and guardrail fallback)."""
    objection = objections[0] if objections else "none"
    if intent == "price_objection":
        objection = "price"
    top = candidates[:1]
    recos, reasons = [], []
    if intent == "purchase_intent" and top:
        c = top[0]
        reply = f"Excellent choice! {_fmt(c)}. I will send you the secure payment link now."
        recos, reasons, action = [c], ["course requested by the customer"], "send_payment_link"
    elif intent == "course_comparison" and len(candidates) >= 2:
        a, b = candidates[0], candidates[1]
        reply = f"{_fmt(a)} vs {_fmt(b)}. {a['title']}: {a['description']} {b['title']}: {b['description']}"
        recos, reasons, action = [a, b], ["compared course", "compared course"], "answer_question"
    elif intent == "payment_issue":
        reply = "Sorry for the inconvenience. I am forwarding your case to our payment team; no new charge will be made."
        action = "route_to_payment_support"
    elif intent == "support_request":
        reply = "Sorry about that! Our support team will help you access your course very quickly."
        action = "route_to_customer_support"
    elif intent == "not_interested":
        reply = "No problem, thank you for your time. We remain available if you change your mind."
        action = "end_conversation"
    elif objection != "none" and candidates:
        c = candidates[0]
        if objection == "price":
            cheaper = sorted([x for x in data.courses() if x["category"] == c["category"]
                              and x["price_tnd"] < c["price_tnd"]], key=lambda x: x["price_tnd"])
            reply = f"I understand. {_fmt(c)}."
            if cheaper:
                reply += f" A lighter option is {_fmt(cheaper[0])}."
                recos, reasons = [c, cheaper[0]], ["matches your goal", "more affordable alternative"]
            else:
                recos, reasons = [c], ["matches your goal"]
            if profile.get("segment") == "student":
                reply += f" Students can use code STUDENT20 (-20%: {c['price_tnd'] * 0.8:.2f} TND)."
        elif objection == "time":
            short = min(candidates, key=lambda x: x["duration_hours"])
            reply = f"I understand you are busy. {_fmt(short)} takes only {short['duration_hours']}h, {short['format']}."
            recos, reasons = [short], ["shortest relevant course"]
        elif objection == "difficulty":
            easy = [x for x in candidates if x["level"] == "beginner"] or \
                   [x for x in data.courses() if x["level"] == "beginner" and x["category"] == c["category"]] or [c]
            reply = f"No worries! {_fmt(easy[0])} is designed for beginners and has no prerequisites." \
                if not easy[0]["prerequisites"] else f"{_fmt(easy[0])} requires: {', '.join(easy[0]['prerequisites'])}."
            recos, reasons = [easy[0]], ["beginner-friendly"]
        else:  # trust
            reply = f"{_fmt(c)} includes a certificate of completion" + ("." if c["certificate"] else " (not included).")
            recos, reasons = [c], ["matches your goal"]
        action = "handle_objection"
    elif candidates:
        recos = candidates[:2]
        reasons = ["best match for your request"] * len(recos)
        reply = "Here is what I recommend: " + "; ".join(_fmt(c) for c in recos) + ". Would you like more details?"
        action = "present_courses"
    else:
        reply, action = "Could you tell me more about your goal so I can recommend the right course?", "answer_question"
    return SalesDraft(reply=reply, detected_intent=intent, objection_type=objection,
                      recommended_course_ids=[c["course_id"] for c in recos], recommendation_reasons=reasons,
                      next_action=action, purchase_intent_score=INTENT_SCORE[intent],
                      confidence=0.6 if intent != "information_request" else 0.45)


class SalesAgent(BaseAgent[SalesInput, SalesOutput]):
    name = "sales_agent"
    input_model = SalesInput
    output_model = SalesOutput
    prompt_name = "sales"
    max_tokens = 1200

    def process(self, inp: SalesInput, meta: AgentMeta) -> SalesOutput:
        profile = inp.customer_profile or (data.customer(inp.customer_id) if inp.customer_id else None) or {}
        if inp.customer_id and not profile:
            meta.warnings.append(f"unknown_customer_id:{inp.customer_id}")
        recent = inp.conversation_history[-4:]
        history_text = " ".join(t.text for t in recent if t.role == "customer")
        intent_hint = detect_intent(inp.customer_message)
        objection_hint = detect_objections(inp.customer_message)

        cmap = data.course_map()
        mentioned = [cmap[i] for i in mentioned_course_ids(inp.customer_message + " " + history_text)]
        candidates = mentioned + [c for c in search_courses(inp.customer_message, profile, 3, history_text)
                                  if c not in mentioned]
        candidates = candidates[:4]
        if intent_hint in NO_RECO_INTENTS:
            mock_candidates = []
        else:
            mock_candidates = candidates

        payload = {
            "customer_message": inp.customer_message,
            "recent_history": [t.model_dump() for t in recent],
            "customer_profile": {k: profile.get(k) for k in ("segment", "experience_level", "interests",
                                                             "budget_max_tnd", "preferred_language") if profile.get(k)},
            "candidates": [{k: c[k] for k in ("course_id", "title", "price_tnd", "level", "duration_weeks",
                                               "duration_hours", "prerequisites", "certificate", "format",
                                               "description")} for c in candidates],
            "offers": DISCOUNT_CODES,
            "rule_hints": {"intent": intent_hint, "objections": objection_hint},
            "channel": inp.channel,
        }
        draft = self.draft(payload=payload, draft_model=SalesDraft, meta=meta, text_fields=SalesDraft.text_fields,
                           mock=lambda: template_draft(intent_hint, objection_hint, mock_candidates, profile))
        meta.decision_source = "llm" if meta.llm_used else "deterministic"

        # ---------------- guardrails: catalog grounding
        grounded = True
        valid_ids = [i for i in dict.fromkeys(draft.recommended_course_ids) if i in cmap][:3]
        if len(valid_ids) != len(set(draft.recommended_course_ids)):
            meta.guardrails_triggered.append("unknown_course_id_removed")
            grounded = False
        bad_prices = [p for p in prices_in_text(draft.reply) if round(p, 2) not in allowed_prices()]
        payment_claim = SUCCESS_CLAIM.search(draft.reply) is not None
        if bad_prices or payment_claim:
            meta.guardrails_triggered.append(
                f"reply_replaced:{'non_catalog_price ' + str(bad_prices) if bad_prices else 'payment_claim'}")
            grounded = False
            safe_candidates = [cmap[i] for i in valid_ids] or mock_candidates
            safe = template_draft(draft.detected_intent, [] if draft.objection_type == "none" else [draft.objection_type],
                                  [] if draft.detected_intent in NO_RECO_INTENTS else safe_candidates, profile)
            draft = draft.model_copy(update={"reply": FALLBACK_PREFIX + safe.reply})
            valid_ids = [i for i in safe.recommended_course_ids if i in cmap] or valid_ids

        reasons = draft.recommendation_reasons
        recos = [CourseRecommendation(course_id=i, title=cmap[i]["title"], price_tnd=cmap[i]["price_tnd"],
                                      level=cmap[i]["level"], duration_weeks=cmap[i]["duration_weeks"],
                                      reason=reasons[n] if n < len(reasons) else "relevant to the request")
                 for n, i in enumerate(valid_ids)]
        return SalesOutput(reply=draft.reply, detected_intent=draft.detected_intent,
                           objection_type=draft.objection_type, recommended_courses=recos,
                           next_action=draft.next_action, purchase_intent_score=draft.purchase_intent_score,
                           confidence=draft.confidence, catalog_grounded=grounded)
