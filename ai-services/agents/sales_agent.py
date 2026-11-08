"""Voice Sales Agent (text first). Grounded on the SIMULATED catalog; prices are verified after generation."""
from __future__ import annotations

from agents.payment_agent import SUCCESS_CLAIM
from core import data
from core.base_agent import FALLBACK_PREFIX, BaseAgent
from data_generation.catalog import DISCOUNT_CODES
from schemas.common import AgentMeta
from schemas.sales import CourseRecommendation, SalesDraft, SalesInput, SalesOutput
from agents.sales_replies import WEEKS, LEVEL, Writer, join, seed_of
from tools.catalog_search import (LEVEL_ORDER, allowed_prices, mentioned_course_ids, prices_in_text, search_courses,
                                  topic_matches)
from tools.text_rules import detect_intent, detect_language, detect_objections, detect_smalltalk

INTENT_SCORE = {"purchase_intent": 0.85, "course_comparison": 0.6, "price_objection": 0.55,
                "information_request": 0.5, "payment_issue": 0.6, "support_request": 0.3, "not_interested": 0.05}
NO_RECO_INTENTS = {"payment_issue", "support_request", "not_interested"}


def template_draft(intent: str, objections: list[str], candidates: list[dict], profile: dict,
                   lang: str = "fr", smalltalk: str | None = None, first_turn: bool = True,
                   seed: int = 0) -> SalesDraft:
    """Deterministic, localized, structured reply built only from catalog facts (mock mode and guardrail fallback)."""
    w = Writer(lang, seed)
    objection = objections[0] if objections else "none"
    if intent == "price_objection":
        objection = "price"
    greet = (w.say("hello") if first_turn else w.say("hello_again")) if smalltalk == "greeting" else ""
    recos, reasons = [], []
    action = "answer_question"

    if intent == "information_request" and smalltalk and not candidates:
        # pure small talk: no course pushed
        if smalltalk == "greeting":
            reply = join(greet + " " + w.say("offer_help"), w.say("ask_goal"))
        elif smalltalk == "thanks":
            reply = join(w.say("thanks") + " " + w.say("thanks_more"))
        elif smalltalk == "farewell":
            reply, action = w.say("farewell"), "end_conversation"
        elif smalltalk == "whoami":
            reply = join(w.say("whoami"), w.say("ask_goal"))
        else:  # catalog
            picks = sorted(data.courses(), key=lambda c: (LEVEL_ORDER[c["level"]], c["price_tnd"]))
            seen, recos = set(), []
            for c in picks:  # one course per category, most accessible first
                if c["category"] not in seen:
                    seen.add(c["category"])
                    recos.append(c)
            recos = recos[:3]
            reasons = [w.reason("popular")] * len(recos)
            reply = join(w.say("catalog", n=len(data.courses())),
                         "\n".join(w.bullet(c, with_desc=False) for c in recos), w.say("close_present"))
            action = "present_courses"
    elif intent == "purchase_intent" and candidates:
        c = candidates[0]
        reply = join(w.say("purchase"), w.bullet(c), w.say("purchase_next"))
        recos, reasons, action = [c], [w.reason("requested")], "send_payment_link"
    elif intent == "course_comparison" and len(candidates) >= 2:
        a, b = candidates[0], candidates[1]
        first, second = sorted((a, b), key=lambda c: (LEVEL_ORDER[c["level"]], len(c["prerequisites"])))
        if first["course_id"] in second["prerequisites"] or LEVEL_ORDER[first["level"]] < LEVEL_ORDER[second["level"]]:
            advice = w.say("advice_path", a=first["title"], b=second["title"])
        else:
            cheap, full = sorted((a, b), key=lambda c: c["price_tnd"])
            advice = w.say("advice_cheap", a=cheap["title"], b=full["title"])
        reply = join(w.say("compare"), w.compare_block(a), w.compare_block(b), advice)
        recos, reasons = [a, b], [w.reason("compared")] * 2
    elif intent == "payment_issue":
        reply, action = w.say("pay_issue"), "route_to_payment_support"
    elif intent == "support_request":
        reply, action = w.say("support"), "route_to_customer_support"
    elif intent == "not_interested":
        reply, action = w.say("not_interested"), "end_conversation"
    elif objection != "none" and candidates:
        c = candidates[0]
        action = "handle_objection"
        if objection == "price":
            cheaper = sorted([x for x in data.courses() if x["category"] == c["category"]
                              and x["price_tnd"] < c["price_tnd"]], key=lambda x: x["price_tnd"])
            parts = [w.say("price_ack"), w.bullet(c, with_desc=False)]
            if cheaper:
                parts += [w.say("price_cheaper") + "\n" + w.bullet(cheaper[0])]
                recos, reasons = [c, cheaper[0]], [w.reason("goal"), w.reason("cheaper")]
            else:
                parts.append(w.say("price_none"))
                recos, reasons = [c], [w.reason("goal")]
            if profile.get("segment") == "student":
                parts.append(w.say("price_student", title=c["title"], price=c["price_tnd"] * 0.8))
            reply = join(*parts)
        elif objection == "time":
            same_topic = [x for x in candidates if x["category"] == c["category"]]  # stay on the asked topic
            short = min(same_topic, key=lambda x: x["duration_hours"])
            reply = join(w.say("time_ack"), w.bullet(short),
                         w.say("time_detail", hpw=w.hours_per_week(short), hours=short["duration_hours"],
                               fmt=w.fmt(short)))
            recos, reasons = [short], [w.reason("short")]
        elif objection == "difficulty":
            easy = [x for x in candidates if x["level"] == "beginner"] or \
                   [x for x in data.courses() if x["level"] == "beginner" and x["category"] == c["category"]] or [c]
            e = easy[0]
            note = w.say("diff_ok") if not e["prerequisites"] else w.say("diff_prereq", prereqs=w.prereqs(e))
            reply = join(w.say("diff_ack"), w.bullet(e), note)
            recos, reasons = [e], [w.reason("beginner")]
        else:  # trust
            cert = w.nth("trust_cert", 0 if c["certificate"] else 1)
            more = w.say("trust_more", fmt=w.fmt(c), weeks=c["duration_weeks"], weeks_word=WEEKS[w.lang],
                         hours=c["duration_hours"], level=LEVEL[w.lang][c["level"]])
            reply = join(w.say("trust"), f"**{c['title']}**\n{cert}\n{more}")
            recos, reasons = [c], [w.reason("goal")]
    elif candidates:
        recos = candidates[:2]
        reasons = [w.reason("starter") if c["level"] == "beginner" and not c["prerequisites"] else w.reason("match")
                   for c in recos]
        parts = [(greet + " " if greet else "") + w.say("present"), "\n".join(w.bullet(c) for c in recos)]
        gated = next((c for c in recos if c["prerequisites"]), None)
        if gated:
            parts.append(w.say("prereq", title=gated["title"], prereqs=w.prereqs(gated)))
        parts.append(w.say("close_present"))
        reply, action = join(*parts), "present_courses"
    else:
        reply = join((greet + " " if greet else "") + w.say("clarify"), w.say("ask_goal"))
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
        lang = detect_language(inp.customer_message, history_text)
        smalltalk = detect_smalltalk(inp.customer_message) if intent_hint == "information_request" else None
        # small talk ("coucou", "merci") with no topic in the message itself: no course pushed
        pure_smalltalk = smalltalk is not None and not mentioned and not topic_matches(inp.customer_message)
        first_turn = not any(t.role == "agent" for t in inp.conversation_history)
        seed = seed_of(inp.customer_message)
        if intent_hint in NO_RECO_INTENTS or pure_smalltalk:
            mock_candidates = []
        else:
            mock_candidates = candidates

        def fallback(intent: str, objections: list[str], cands: list[dict]) -> SalesDraft:
            return template_draft(intent, objections, cands, profile, lang=lang, smalltalk=smalltalk,
                                  first_turn=first_turn, seed=seed)

        payload = {
            "customer_message": inp.customer_message,
            "recent_history": [t.model_dump() for t in recent],
            "customer_profile": {k: profile.get(k) for k in ("segment", "experience_level", "interests",
                                                             "budget_max_tnd", "preferred_language") if profile.get(k)},
            "candidates": [{k: c[k] for k in ("course_id", "title", "price_tnd", "level", "duration_weeks",
                                               "duration_hours", "prerequisites", "certificate", "format",
                                               "description")} for c in candidates],
            "offers": DISCOUNT_CODES,
            "rule_hints": {"intent": intent_hint, "objections": objection_hint, "language": lang,
                           "small_talk": smalltalk if pure_smalltalk else None, "first_turn": first_turn},
            "channel": inp.channel,
        }
        draft = self.draft(payload=payload, draft_model=SalesDraft, meta=meta, text_fields=SalesDraft.text_fields,
                           mock=lambda: fallback(intent_hint, objection_hint, mock_candidates))
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
            safe = fallback(draft.detected_intent, [] if draft.objection_type == "none" else [draft.objection_type],
                            [] if draft.detected_intent in NO_RECO_INTENTS else safe_candidates)
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
