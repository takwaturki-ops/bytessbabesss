"""Security & Fraud Detection Agent. Decisions: deterministic Python rules. LLM: explanation text only."""
from __future__ import annotations

from core.base_agent import BaseAgent
from schemas.common import AgentMeta
from schemas.fraud import FraudCheckInput, FraudDraft, FraudOutput
from tools.fraud_rules import decide, evaluate

LABEL = {"allow": "ALLOW", "block": "BLOCK", "require_human_approval": "REVIEW"}


class FraudAgent(BaseAgent[FraudCheckInput, FraudOutput]):
    name = "fraud_agent"
    input_model = FraudCheckInput
    output_model = FraudOutput
    prompt_name = "fraud"
    max_tokens = 800

    def process(self, inp: FraudCheckInput, meta: AgentMeta) -> FraudOutput:
        hits = evaluate(inp)
        action, score, level = decide(hits)   # final decision - never touched by the LLM
        ev = inp.event

        def template() -> FraudDraft:
            if not hits:
                return FraudDraft(explanation="No fraud rule was triggered; the transaction matches normal behaviour.",
                                  alert_summary=f"ALLOW - {ev.transaction_id}")
            details = "; ".join(f"{h.rule_id}: {h.detail}" for h in hits)
            return FraudDraft(explanation=f"Decision {action} (risk {score}/100) because {details}.",
                              alert_summary=f"{LABEL[action]} - {', '.join(h.rule_id for h in hits)} on order {ev.order_id}")

        # Token saving: LLM is only used to explain alerts, never for clean transactions.
        if hits and inp.explain:
            payload = {"action": action, "risk_score": score, "transaction_id": ev.transaction_id,
                       "order_id": ev.order_id, "amount_tnd": ev.amount_tnd,
                       "rule_hits": [h.model_dump() for h in hits]}
            draft = self.draft(payload=payload, draft_model=FraudDraft, mock=template, meta=meta,
                               text_fields=FraudDraft.text_fields)
        else:
            draft = template()
        meta.decision_source = "deterministic"

        # Guardrail: the explanation must not contradict the rule decision.
        text = f"{draft.explanation} {draft.alert_summary}".lower()
        contradiction = (action != "allow" and any(p in text for p in ("should be allowed", "safe to approve",
                                                                         "no fraud", "approve this transaction")))
        if contradiction:
            meta.guardrails_triggered.append("contradictory_explanation_replaced")
            draft = template()

        return FraudOutput(
            transaction_id=ev.transaction_id, action=action, risk_score=score, risk_level=level,
            flags=sorted({h.rule_id for h in hits}), rule_hits=hits, explanation=draft.explanation,
            alert_summary=draft.alert_summary if action != "allow" else None,
        )
