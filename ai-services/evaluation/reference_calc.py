"""Independent pure-Python implementation of key financial metrics (no pandas).

Used to cross-check the pandas engine of the Financial Data Analyst.
"""
from __future__ import annotations


def reference_metrics(orders: list[dict], transactions: list[dict]) -> dict:
    order_ids = {o["order_id"] for o in orders}
    txns = [t for t in transactions if t["order_id"] in order_ids]
    paid = [o for o in orders if o["status"] == "paid"]
    revenue = round(sum(float(o["amount_tnd"]) for o in paid), 2)
    success = sum(1 for t in txns if t["status"] == "success")
    first_ok = len({t["order_id"] for t in txns if t["attempt_no"] == 1 and t["status"] == "success"})
    with_txn = len({t["order_id"] for t in txns})
    return {
        "total_orders": len(orders),
        "paid_orders": len(paid),
        "gross_revenue_tnd": revenue,
        "average_order_value_tnd": round(revenue / len(paid), 2) if paid else 0.0,
        "order_conversion_rate": round(len(paid) / len(orders), 4) if orders else 0.0,
        "total_transactions": len(txns),
        "successful_transactions": success,
        "failed_transactions": sum(1 for t in txns if t["status"] == "failed"),
        "payment_success_rate": round(success / len(txns), 4) if txns else 0.0,
        "first_attempt_success_rate": round(first_ok / with_txn, 4) if with_txn else 0.0,
        "pending_amount_tnd": round(sum(float(o["amount_tnd"]) for o in orders if o["status"] == "pending"), 2),
        "at_risk_amount_tnd": round(sum(float(o["amount_tnd"]) for o in orders if o["status"] == "requires_review"), 2),
    }
