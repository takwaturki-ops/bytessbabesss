"""Deterministic course retrieval: only the top-k relevant courses are sent to the LLM (token saving)."""
from __future__ import annotations

import re

from core import data
from tools.text_rules import has, norm

LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
PRICE_PATTERN = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*(?:tnd|dt|dinars?|د\.?ت|دينار)", re.IGNORECASE)


def search_courses(text: str, profile: dict | None = None, top_k: int = 3,
                   history_text: str = "") -> list[dict]:
    t = norm(text + " " + history_text)
    profile = profile or {}
    interests = set(profile.get("interests", []))
    level = profile.get("experience_level")
    budget = profile.get("budget_max_tnd")
    scored = []
    for c in data.courses():
        s = 0.0
        if has(t, norm(c["title"])):
            s += 10
        s += 5 * sum(1 for k in c["keywords"] if has(t, k.lower()))  # explicit topic beats profile signals
        if c["category"] in interests:
            s += 2
        if level and LEVEL_ORDER[c["level"]] <= LEVEL_ORDER.get(level, 0):
            s += 1
        if level == "beginner" and c["level"] == "advanced":
            s -= 2
        if budget and c["price_tnd"] <= budget:
            s += 1
        scored.append((s, c["price_tnd"], c))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for s, _, c in scored[:top_k] if s > 0] or [c for _, _, c in scored[:top_k]]


def mentioned_course_ids(text: str) -> list[str]:
    t = norm(text)
    return [c["course_id"] for c in data.courses() if has(t, norm(c["title"]))]


def allowed_prices(course_ids: list[str] | None = None) -> set[float]:
    """Catalog prices and their valid discounted prices (only codes defined in the catalog)."""
    from data_generation.catalog import DISCOUNT_CODES

    cmap = data.course_map()
    ids = course_ids or list(cmap)
    out: set[float] = set()
    for cid in ids:
        p = cmap[cid]["price_tnd"]
        out.add(round(p, 2))
        out.update(round(p * (1 - d), 2) for d in DISCOUNT_CODES.values())
    return out


def prices_in_text(text: str) -> list[float]:
    return [float(m.replace(",", ".")) for m in PRICE_PATTERN.findall(text)]


def topic_matches(text: str) -> list[dict]:
    """Courses whose title or a keyword appears in the text itself (no profile signals, no fallback)."""
    t = norm(text)
    return [c for c in data.courses()
            if has(t, norm(c["title"])) or any(has(t, k.lower()) for k in c["keywords"])]
