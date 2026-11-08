"""Validate SIMULATED datasets: IDs, relationships, price/amount consistency, labels, split hygiene."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"

VALID_INTENTS = {"purchase_intent", "information_request", "price_objection", "course_comparison",
                 "payment_issue", "not_interested", "support_request"}
VALID_TXN_STATUS = {"success", "failed", "pending", "requires_review"}
VALID_ORDER_STATUS = {"paid", "failed", "pending", "requires_review"}
VALID_ACTIONS = {"allow", "block", "require_human_approval"}


def load(rel: str) -> list[dict]:
    payload = json.loads((DATA / rel).read_text(encoding="utf-8"))
    assert payload["_meta"]["simulated"] is True, f"{rel}: _meta.simulated must be true"
    return payload["records"]


def validate() -> list[str]:
    errors: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    courses = load("reference/courses.json")
    customers = load("reference/customers.json")
    course_ids = {c["course_id"] for c in courses}
    cust_ids = {c["customer_id"] for c in customers}
    price = {c["course_id"]: c["price_tnd"] for c in courses}

    check(10 <= len(courses) <= 15, f"courses count {len(courses)} not in 10-15")
    check(len(customers) == 100, f"customers count {len(customers)} != 100")
    check(len(course_ids) == len(courses), "duplicate course_id")
    check(len(cust_ids) == len(customers), "duplicate customer_id")
    for c in courses:
        check(c["price_tnd"] > 0, f"{c['course_id']} non-positive price")
        for p in c["prerequisites"]:
            check(p in course_ids, f"{c['course_id']} unknown prerequisite {p}")

    all_conv, all_orders, all_txn, all_fraud = [], [], [], []
    split_ids: dict[str, set] = {}
    for split in ("dev", "eval"):
        conv = load(f"{split}/conversations.json")
        orders = load(f"{split}/orders.json")
        txns = load(f"{split}/transactions.json")
        fraud = load(f"{split}/fraud_scenarios.json")
        split_ids[split] = {r["conversation_id"] for r in conv} | {r["order_id"] for r in orders} | \
            {r["scenario_id"] for r in fraud}
        all_conv += conv; all_orders += orders; all_txn += txns; all_fraud += fraud

        order_ids = {o["order_id"] for o in orders}
        for t in txns:
            check(t["order_id"] in order_ids, f"{t['transaction_id']} order {t['order_id']} not in {split} split")

    check(not (split_ids["dev"] & split_ids["eval"]), "dev/eval splits overlap")
    check(len(all_conv) == 150, f"conversations {len(all_conv)} != 150")
    check(len(all_orders) == 100, f"orders {len(all_orders)} != 100")
    check(40 <= len(all_fraud) <= 60, f"fraud scenarios {len(all_fraud)} not in 40-60")

    conv_ids = {c["conversation_id"] for c in all_conv}
    for c in all_conv:
        lab = c["labels"]
        check(c["customer_id"] in cust_ids, f"{c['conversation_id']} unknown customer")
        check(lab["intent"] in VALID_INTENTS, f"{c['conversation_id']} bad intent")
        check(lab["sentiment"] in {"positive", "neutral", "negative"}, f"{c['conversation_id']} bad sentiment")
        check(0 <= lab["interest_score"] <= 100, f"{c['conversation_id']} interest out of range")
        check(lab["mentioned_course_id"] is None or lab["mentioned_course_id"] in course_ids,
              f"{c['conversation_id']} unknown course")
        check(c["turns"] and c["turns"][0]["role"] == "customer", f"{c['conversation_id']} must start with customer")
        for turn in c["turns"]:  # any price the agent quotes must match the catalog
            if turn["role"] == "agent" and "TND" in turn["text"] and lab["mentioned_course_id"]:
                check(f"{price[lab['mentioned_course_id']]:.0f} TND" in turn["text"],
                      f"{c['conversation_id']} agent quoted a non-catalog price")

    txn_by_order: dict[str, list[dict]] = {}
    for t in all_txn:
        txn_by_order.setdefault(t["order_id"], []).append(t)
        check(t["status"] in VALID_TXN_STATUS, f"{t['transaction_id']} bad status")
        check((t["status"] == "success") == bool(t["provider_reference"]),
              f"{t['transaction_id']} provider_reference must exist iff success")
        datetime.fromisoformat(t["created_at"])
    for o in all_orders:
        check(o["customer_id"] in cust_ids, f"{o['order_id']} unknown customer")
        check(o["course_id"] in course_ids, f"{o['order_id']} unknown course")
        check(o["list_price_tnd"] == price[o["course_id"]], f"{o['order_id']} list price != catalog")
        check(o["amount_tnd"] <= o["list_price_tnd"], f"{o['order_id']} amount above list price")
        check(o["status"] in VALID_ORDER_STATUS, f"{o['order_id']} bad status")
        check(o["conversation_id"] is None or o["conversation_id"] in conv_ids, f"{o['order_id']} unknown conversation")
        ts = txn_by_order.get(o["order_id"], [])
        check(bool(ts), f"{o['order_id']} has no transactions")
        n_success = sum(t["status"] == "success" for t in ts)
        check(n_success <= 1, f"{o['order_id']} has {n_success} successful transactions")
        check((o["status"] == "paid") == (n_success == 1), f"{o['order_id']} status/transaction mismatch")
        for t in ts:
            check(t["expected_amount_tnd"] == o["amount_tnd"], f"{t['transaction_id']} expected amount != order")
            if t["status"] == "success":
                check(t["amount_tnd"] == o["amount_tnd"], f"{t['transaction_id']} success with wrong amount")

    fraud_ids = [f["scenario_id"] for f in all_fraud]
    check(len(fraud_ids) == len(set(fraud_ids)), "duplicate fraud scenario id")
    labels = {f["label"] for f in all_fraud}
    check(labels == {"normal", "suspicious"}, "fraud scenarios need both normal and suspicious")
    for f in all_fraud:
        check(f["expected_action"] in VALID_ACTIONS, f"{f['scenario_id']} bad action")
        check(f["customer_context"]["customer_id"] in cust_ids, f"{f['scenario_id']} unknown customer")
        check(f["event"]["course_id"] in course_ids, f"{f['scenario_id']} unknown course")
        check((f["label"] == "normal") == (f["expected_action"] == "allow"), f"{f['scenario_id']} label/action mismatch")
    return errors


if __name__ == "__main__":
    errs = validate()
    if errs:
        print(f"VALIDATION FAILED ({len(errs)} errors):")
        for e in errs[:50]:
            print(" -", e)
        sys.exit(1)
    print("VALIDATION PASSED: all synthetic datasets are consistent.")
