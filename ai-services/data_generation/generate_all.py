"""Generate every SIMULATED dataset (seed=42) into data/synthetic/.

Layout:
  reference/  courses, customers           (shared by dev and eval)
  dev/        conversations, orders, transactions, fraud_scenarios
  eval/       same files, held out (every 5th record) - never used in prompts
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_generation.catalog import COURSES  # noqa: E402
from data_generation.generators import (  # noqa: E402
    SEED, generate_conversations, generate_customers, generate_fraud_scenarios, generate_orders_and_transactions,
)

OUT = ROOT / "data" / "synthetic"
NOTICE = "SIMULATED DATA generated for the 9antra hackathon prototype. Not real people, prices or payments."


def _write_json(path: Path, records: list[dict], name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"_meta": {"dataset": name, "simulated": True, "seed": SEED, "notice": NOTICE, "count": len(records)},
               "records": records}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        return
    fields = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: (";".join(map(str, v)) if isinstance(v, list) else v) for k, v in r.items()})


def _split(records: list[dict]) -> tuple[list[dict], list[dict]]:
    dev = [r for i, r in enumerate(records) if i % 5 != 4]
    ev = [r for i, r in enumerate(records) if i % 5 == 4]
    return dev, ev


def main() -> dict:
    rng = random.Random(SEED)
    courses = [dict(c, simulated=True) for c in COURSES]
    customers = generate_customers(rng, 100)
    conversations = generate_conversations(rng, customers, 150)
    orders, txns = generate_orders_and_transactions(rng, customers, conversations, 100)
    fraud = generate_fraud_scenarios(rng, customers)

    _write_json(OUT / "reference" / "courses.json", courses, "courses")
    _write_csv(OUT / "reference" / "courses.csv", courses)
    _write_json(OUT / "reference" / "customers.json", customers, "customers")
    _write_csv(OUT / "reference" / "customers.csv", customers)

    conv_dev, conv_eval = _split(conversations)
    ord_dev, ord_eval = _split(orders)
    eval_ids = {o["order_id"] for o in ord_eval}
    txn_dev = [t for t in txns if t["order_id"] not in eval_ids]
    txn_eval = [t for t in txns if t["order_id"] in eval_ids]
    fr_dev, fr_eval = _split(fraud)

    counts = {}
    for split, conv, ords, tx, fr in (("dev", conv_dev, ord_dev, txn_dev, fr_dev),
                                      ("eval", conv_eval, ord_eval, txn_eval, fr_eval)):
        d = OUT / split
        _write_json(d / "conversations.json", conv, "conversations")
        _write_json(d / "orders.json", ords, "orders")
        _write_csv(d / "orders.csv", ords)
        _write_json(d / "transactions.json", tx, "transactions")
        _write_csv(d / "transactions.csv", tx)
        _write_json(d / "fraud_scenarios.json", fr, "fraud_scenarios")
        counts[split] = {"conversations": len(conv), "orders": len(ords), "transactions": len(tx),
                         "fraud_scenarios": len(fr)}
    counts["reference"] = {"courses": len(courses), "customers": len(customers)}
    manifest = {"simulated": True, "seed": SEED, "notice": NOTICE, "counts": counts}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
