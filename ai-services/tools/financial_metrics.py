"""pandas calculations for the Financial Data Analyst. All numbers come from here, never from the LLM."""
from __future__ import annotations

import pandas as pd

from schemas.financial import Breakdown, FinancialMetrics

ORDER_COLS = ["order_id", "course_id", "amount_tnd", "list_price_tnd", "payment_method", "status", "created_at"]
TXN_COLS = ["transaction_id", "order_id", "attempt_no", "status", "amount_tnd", "failure_reason", "created_at"]


def _rate(num: float, den: float) -> float:
    return round(num / den, 4) if den else 0.0


def _breakdown(paid: pd.DataFrame, key: str, labels: dict[str, str] | None = None) -> list[Breakdown]:
    if paid.empty:
        return []
    g = paid.groupby(key).agg(revenue=("amount_tnd", "sum"), n=("order_id", "count")).reset_index()
    g = g.sort_values(["revenue", key], ascending=[False, True])
    return [Breakdown(key=str(r[key]), label=(labels or {}).get(str(r[key]), str(r[key])),
                      revenue_tnd=round(float(r["revenue"]), 2), paid_orders=int(r["n"])) for _, r in g.iterrows()]


def filter_dates(df: pd.DataFrame, date_from: str | None, date_to: str | None) -> pd.DataFrame:
    if df.empty:
        return df
    ts = pd.to_datetime(df["created_at"])
    mask = pd.Series(True, index=df.index)
    if date_from:
        mask &= ts >= pd.Timestamp(date_from)
    if date_to:
        mask &= ts < pd.Timestamp(date_to) + pd.Timedelta(days=1)
    return df[mask]


def unmatched_transactions(orders: list[dict], transactions: list[dict]) -> tuple[list[str], list[str]]:
    """Read-only check: transactions whose order_id matches NO supplied order (exact, case-sensitive match,
    same as the filter in compute_metrics). Returns (excluded transaction_ids, unmatched order_ids).
    Date filtering is intentionally not considered here: only references to orders that were never supplied."""
    known = {o.get("order_id") for o in orders}
    excluded = [t for t in transactions if t.get("order_id") not in known]
    tx_ids = [str(t.get("transaction_id")) for t in excluded]
    order_ids = list(dict.fromkeys(str(t.get("order_id")) for t in excluded))
    return tx_ids, order_ids


def _preview(ids: list[str], limit: int = 20) -> str:
    return ", ".join(ids[:limit]) + (f" (+{len(ids) - limit} more)" if len(ids) > limit else "")


def unmatched_warning(orders: list[dict], transactions: list[dict]) -> str | None:
    tx_ids, order_ids = unmatched_transactions(orders, transactions)
    if not tx_ids:
        return None
    return (f"transactions_excluded_unmatched_order:{len(tx_ids)} - transaction_ids: {_preview(tx_ids)}; "
            f"unmatched order_ids: {_preview(order_ids)}. These transactions were not counted in any metric; "
            f"send their orders (order_id match is exact and case-sensitive).")


def compute_metrics(orders: list[dict], transactions: list[dict], courses: dict[str, dict],
                    conversations: list[dict] | None = None, date_from: str | None = None,
                    date_to: str | None = None) -> FinancialMetrics:
    o = pd.DataFrame(orders, columns=None) if orders else pd.DataFrame(columns=ORDER_COLS)
    missing = [c for c in ORDER_COLS if c not in o.columns]
    if missing:
        raise ValueError(f"orders missing columns: {missing}")
    o = filter_dates(o, date_from, date_to)
    t = pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=TXN_COLS)
    missing = [c for c in TXN_COLS if c not in t.columns]
    if missing:
        raise ValueError(f"transactions missing columns: {missing}")
    t = t[t["order_id"].isin(set(o["order_id"]))]  # keep transactions of the selected orders only

    o["amount_tnd"] = o["amount_tnd"].astype(float)
    o["list_price_tnd"] = o["list_price_tnd"].astype(float)
    paid = o[o["status"] == "paid"].copy()
    paid["category"] = paid["course_id"].map(lambda c: courses.get(c, {}).get("category", "unknown"))
    paid["month"] = pd.to_datetime(paid["created_at"]).dt.strftime("%Y-%m") if not paid.empty else []

    n_orders, n_paid = len(o), len(paid)
    revenue = round(float(paid["amount_tnd"].sum()), 2)
    list_value = round(float(paid["list_price_tnd"].sum()), 2)

    orders_with_txn = t["order_id"].nunique()
    first_ok = t[(t["attempt_no"] == 1) & (t["status"] == "success")]["order_id"].nunique()
    fails = t[t["status"] == "failed"]["failure_reason"].fillna("unspecified").value_counts()

    conv_rate = None
    if conversations:
        conv_rate = _rate(sum(c["labels"]["outcome"] == "converted" for c in conversations), len(conversations))

    titles = {cid: c["title"] for cid, c in courses.items()}
    return FinancialMetrics(
        total_orders=n_orders, paid_orders=n_paid,
        failed_orders=int((o["status"] == "failed").sum()), pending_orders=int((o["status"] == "pending").sum()),
        review_orders=int((o["status"] == "requires_review").sum()),
        gross_revenue_tnd=revenue, list_value_of_paid_orders_tnd=list_value,
        discount_total_tnd=round(list_value - revenue, 2),
        average_order_value_tnd=round(revenue / n_paid, 2) if n_paid else 0.0,
        order_conversion_rate=_rate(n_paid, n_orders),
        total_transactions=len(t), successful_transactions=int((t["status"] == "success").sum()),
        failed_transactions=int((t["status"] == "failed").sum()),
        pending_transactions=int((t["status"] == "pending").sum()),
        review_transactions=int((t["status"] == "requires_review").sum()),
        payment_success_rate=_rate(int((t["status"] == "success").sum()), len(t)),
        first_attempt_success_rate=_rate(first_ok, orders_with_txn),
        pending_amount_tnd=round(float(o[o["status"] == "pending"]["amount_tnd"].sum()), 2),
        at_risk_amount_tnd=round(float(o[o["status"] == "requires_review"]["amount_tnd"].sum()), 2),
        conversation_conversion_rate=conv_rate,
        revenue_by_course=_breakdown(paid, "course_id", titles),
        revenue_by_category=_breakdown(paid, "category"),
        revenue_by_payment_method=_breakdown(paid, "payment_method"),
        revenue_by_month=sorted(_breakdown(paid, "month"), key=lambda b: b.key),
        failure_reasons={str(k): int(v) for k, v in fails.items()},
    )
