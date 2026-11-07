"""Generic check engine for evaluation scenarios.

A check is {"path": "data.final_status", "op": "eq", "value": "success"}.
Paths use dots, list indexes ("items[0]") and wildcards ("items[*].course_id").
"""
from __future__ import annotations

import re
from typing import Any

_MISSING = object()


def get_path(obj: Any, path: str) -> Any:
    cur: Any = obj
    for part in re.findall(r"[^.\[\]]+|\[\*\]|\[\d+\]", path):
        if part == "[*]":
            if not isinstance(cur, list):
                return _MISSING
            rest = path.split("[*]", 1)[1].lstrip(".")
            return [get_path(x, rest) if rest else x for x in cur]
        if part.startswith("["):
            idx = int(part[1:-1])
            cur = cur[idx] if isinstance(cur, list) and idx < len(cur) else _MISSING
        elif isinstance(cur, dict):
            cur = cur.get(part, _MISSING)
        else:
            return _MISSING
        if cur is _MISSING:
            return _MISSING
    return cur


def _approx(a, b, tol=0.011) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


OPS = {
    "eq": lambda a, v: a == v or (isinstance(v, float) and _approx(a, v)),
    "ne": lambda a, v: a != v,
    "approx": lambda a, v: _approx(a, v[0], v[1]) if isinstance(v, list) else _approx(a, v),
    "in": lambda a, v: a in v,
    "contains": lambda a, v: a is not None and v in a,
    "not_contains": lambda a, v: a is None or v not in a,
    "contains_all": lambda a, v: a is not None and all(x in a for x in v),
    "contains_any": lambda a, v: a is not None and any(x in a for x in v),
    "subset": lambda a, v: a is not None and set(a) <= set(v),
    "gte": lambda a, v: a is not None and a >= v,
    "lte": lambda a, v: a is not None and a <= v,
    "len_eq": lambda a, v: a is not None and len(a) == v,
    "len_gte": lambda a, v: a is not None and len(a) >= v,
    "startswith": lambda a, v: isinstance(a, str) and a.startswith(v),
    "regex_absent": lambda a, v: isinstance(a, str) and re.search(v, a, re.IGNORECASE) is None,
    "regex_present": lambda a, v: isinstance(a, str) and re.search(v, a, re.IGNORECASE) is not None,
    "is_null": lambda a, v: (a is None) == bool(v),
}


def run_checks(response: dict, checks: list[dict]) -> list[dict]:
    results = []
    for c in checks:
        actual = get_path(response, c["path"])
        try:
            ok = actual is not _MISSING and OPS[c["op"]](actual, c.get("value"))
            if c["op"] == "is_null" and actual is _MISSING:
                ok = False
        except Exception:  # a type error in comparison counts as failure
            ok = False
        results.append({"path": c["path"], "op": c["op"], "expected": c.get("value"),
                        "actual": None if actual is _MISSING else actual, "passed": bool(ok)})
    return results
