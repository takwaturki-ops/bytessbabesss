"""Financial Data Analyst: pandas computes, LLM explains validated numbers only."""
from __future__ import annotations

import re

from core import data
from core.base_agent import BaseAgent
from schemas.common import AgentMeta
from schemas.financial import DataScope, FinancialDraft, FinancialMetrics, FinancialOutput, FinancialQuery
from tools.financial_metrics import compute_metrics

NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def _allowed_numbers(metrics: FinancialMetrics) -> set[float]:
    """Every number (and common renderings of it) that the narrative is allowed to mention."""
    vals: list[float] = []

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            vals.append(float(x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(metrics.model_dump())
    allowed: set[float] = set()
    for v in vals:
        for cand in (v, v * 100):  # rates may be rendered as percentages
            allowed.update({round(cand, 2), round(cand, 1), float(round(cand))})
    allowed.update(float(i) for i in range(0, 13))  # small counts / months / "top 3"
    allowed.update({2025.0, 2026.0})
    return allowed


def unverified_numbers(text: str, metrics: FinancialMetrics) -> list[str]:
    allowed = _allowed_numbers(metrics)
    bad = []
    for m in NUMBER.findall(text):
        try:
            v = float(m.replace(",", ""))
        except ValueError:
            continue
        if not any(abs(v - a) <= 0.011 for a in allowed):
            bad.append(m)
    return bad


def deterministic_report(m: FinancialMetrics) -> FinancialDraft:
    top = m.revenue_by_course[0] if m.revenue_by_course else None
    narrative = (f"{m.paid_orders} of {m.total_orders} orders were paid, generating {m.gross_revenue_tnd} TND "
                 f"(average order value {m.average_order_value_tnd} TND). Order conversion is "
                 f"{m.order_conversion_rate * 100:.2f}% and the payment success rate is "
                 f"{m.payment_success_rate * 100:.2f}% across {m.total_transactions} transactions.")
    insights = []
    if top:
        insights.append(f"Top course by revenue: {top.label} ({top.revenue_tnd} TND, {top.paid_orders} orders).")
    if m.failed_transactions:
        reason = max(m.failure_reasons, key=m.failure_reasons.get) if m.failure_reasons else "unspecified"
        insights.append(f"{m.failed_transactions} failed transactions; most common reason: {reason}.")
    if m.review_orders:
        insights.append(f"{m.review_orders} orders ({m.at_risk_amount_tnd} TND) need manual payment review.")
    if m.pending_orders:
        insights.append(f"{m.pending_orders} orders ({m.pending_amount_tnd} TND) are still pending.")
    return FinancialDraft(narrative=narrative, insights=insights[:4] or ["No notable issues in this period."])


class FinancialAnalystAgent(BaseAgent[FinancialQuery, FinancialOutput]):
    name = "financial_analyst_agent"
    input_model = FinancialQuery
    output_model = FinancialOutput
    prompt_name = "financial"
    max_tokens = 1200

    def process(self, q: FinancialQuery, meta: AgentMeta) -> FinancialOutput:
        if q.orders is not None:
            orders, txns, convs, source = q.orders, q.transactions or [], None, "inline"
        else:
            orders = data.split_records("orders", q.split)
            txns = data.split_records("transactions", q.split)
            convs = data.split_records("conversations", q.split)
            source = f"simulated:{q.split}"
        metrics = compute_metrics(orders, txns, data.course_map(), convs, q.date_from, q.date_to)

        if q.explain:
            # Token saving: send compact metrics (top-5 breakdowns), never raw rows.
            compact = metrics.model_dump()
            for k in ("revenue_by_course", "revenue_by_category", "revenue_by_payment_method"):
                compact[k] = compact[k][:5]
            draft = self.draft(payload={"question": q.question, "metrics": compact}, draft_model=FinancialDraft,
                               mock=lambda: deterministic_report(metrics), meta=meta,
                               text_fields=FinancialDraft.text_fields)
            meta.decision_source = "hybrid" if meta.llm_used else "deterministic"
        else:
            draft = deterministic_report(metrics)

        # Guardrail: every number in LLM text must come from the computed metrics.
        bad = unverified_numbers(draft.narrative + " " + " ".join(draft.insights), metrics)
        if bad:
            meta.guardrails_triggered.append(f"unverified_numbers_replaced:{','.join(bad[:5])}")
            draft = deterministic_report(metrics)

        return FinancialOutput(
            question=q.question, metrics=metrics, insights=draft.insights, narrative=draft.narrative,
            data_scope=DataScope(source=source, n_orders=metrics.total_orders, n_transactions=metrics.total_transactions,
                                 date_from=q.date_from, date_to=q.date_to),
        )
