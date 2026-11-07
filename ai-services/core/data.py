"""Read-only access to the SIMULATED datasets in data/synthetic/ (cached)."""
from __future__ import annotations

import json
from functools import lru_cache

from core.config import ROOT

DATA = ROOT / "data" / "synthetic"


@lru_cache(maxsize=None)
def _load(rel: str) -> tuple[dict, ...]:
    path = DATA / rel
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - run: python main.py generate")
    return tuple(json.loads(path.read_text(encoding="utf-8"))["records"])


def courses() -> list[dict]:
    return list(_load("reference/courses.json"))


def course_map() -> dict[str, dict]:
    return {c["course_id"]: c for c in _load("reference/courses.json")}


def customers() -> list[dict]:
    return list(_load("reference/customers.json"))


def customer(customer_id: str) -> dict | None:
    return next((c for c in _load("reference/customers.json") if c["customer_id"] == customer_id), None)


def split_records(name: str, split: str = "dev") -> list[dict]:
    """name in {conversations, orders, transactions, fraud_scenarios}; split in {dev, eval, all}."""
    if split == "all":
        return list(_load(f"dev/{name}.json")) + list(_load(f"eval/{name}.json"))
    if split not in ("dev", "eval"):
        raise ValueError(f"unknown split {split!r}")
    return list(_load(f"{split}/{name}.json"))
