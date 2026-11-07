"""Payment Agent: interprets SIMULATED payment events. Status is decided by Python rules only."""
from __future__ import annotations

import re

from core.base_agent import BaseAgent
from schemas.common import AgentMeta
from schemas.payment import PaymentDraft, PaymentEvent, PaymentOutput
from tools.payment_rules import ACTION, interpret

# Phrases that claim success. If they appear while the payment is NOT confirmed, the text is rejected.
SUCCESS_CLAIM = re.compile(
    r"\b(payment (was |is |has been )?(successful|succeeded|confirmed|complete[d]?|received)|"
    r"paiement (a été |est )?(réussi|confirmé|validé|accepté|reçu)|successfully paid|you('re| are) enrolled|"
    r"access (is |has been )?granted)\b|تم الدفع|تم تأكيد", re.IGNORECASE)

TEMPLATES = {
    "success": ("Payment {tx} for order {order} confirmed: {amt} TND, provider reference {ref}.",
                "Merci ! Votre paiement de {amt} TND est confirmé. Votre accès au cours est activé."),
    "failed": ("Payment {tx} for order {order} failed ({reason}). No funds captured.",
               "Votre paiement n'a pas abouti. Vous pouvez réessayer ou choisir un autre moyen de paiement."),
    "pending": ("Payment {tx} for order {order} is pending provider confirmation.",
                "Votre paiement est en cours de traitement. Nous vous confirmerons dès sa validation."),
    "requires_review": ("Payment {tx} for order {order} needs manual review: {reasons}.",
                        "Votre paiement est en cours de vérification. Notre équipe revient vers vous rapidement."),
}


class PaymentAgent(BaseAgent[PaymentEvent, PaymentOutput]):
    name = "payment_agent"
    input_model = PaymentEvent
    output_model = PaymentOutput
    prompt_name = "payment"
    max_tokens = 800

    def process(self, ev: PaymentEvent, meta: AgentMeta) -> PaymentOutput:
        final_status, confirmed, evidence, reasons = interpret(ev)

        def template() -> PaymentDraft:
            s, c = TEMPLATES[final_status]
            fmt = dict(tx=ev.transaction_id, order=ev.order_id, amt=ev.amount_tnd, ref=ev.provider_reference,
                       reason=ev.failure_reason or "unspecified", reasons=", ".join(reasons) or "provider flag")
            return PaymentDraft(summary=s.format(**fmt), customer_message=c.format(**fmt))

        if ev.explain:
            payload = {"final_status": final_status, "payment_confirmed": confirmed, "review_reasons": reasons,
                       "transaction_id": ev.transaction_id, "order_id": ev.order_id, "amount_tnd": ev.amount_tnd,
                       "currency": ev.currency, "failure_reason": ev.failure_reason, "language": ev.language}
            draft = self.draft(payload=payload, draft_model=PaymentDraft, mock=template, meta=meta,
                               text_fields=PaymentDraft.text_fields)
            meta.decision_source = "hybrid" if meta.llm_used else "deterministic"
        else:
            draft = template()

        # Guardrail: text may never claim success unless rules confirmed it.
        if not confirmed and (SUCCESS_CLAIM.search(draft.summary) or SUCCESS_CLAIM.search(draft.customer_message)):
            meta.guardrails_triggered.append("unverified_success_claim_removed")
            draft = template()

        return PaymentOutput(
            transaction_id=ev.transaction_id, order_id=ev.order_id, reported_status=ev.status,
            final_status=final_status, payment_confirmed=confirmed, evidence=evidence, review_reasons=reasons,
            recommended_action=ACTION[final_status], amount_tnd=ev.amount_tnd, currency=ev.currency,
            summary=draft.summary, customer_message=draft.customer_message,
        )
