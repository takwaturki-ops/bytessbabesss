"""Multilingual keyword heuristics (EN / FR / Tunisian darija in Latin script).

Used (a) as the MOCK-mode baseline for intent/objection/sentiment and (b) as cheap hints passed to the LLM.
They are deliberately simple; live mode (Claude) handles free-form language.
"""
from __future__ import annotations

import re
import unicodedata

INTENT_RULES: list[tuple[str, tuple[str, ...]]] = [  # order matters: first match wins
    ("not_interested", ("not interested", "intéresse pas", "interesse pas", "ma yhemnich", "stop sending",
                        "unsubscribe", "ne plus recevoir")),
    ("payment_issue", ("declined", "refusé", "refusee", "a échoué", "a echoue", "failed", "pending",
                       "ma t3addech", "not go through", "payment says", "débité", "debite", "charged twice")),
    ("support_request", ("access", "accéder", "acceder", "log in", "login", "nodkhol", "password",
                         "mot de passe", "videos", "vidéos", "connexion")),
    ("course_comparison", ("difference", "différence", "far9", "compare", "versus", " vs ", "which one",
                           "laquelle", "lequel")),
    ("price_objection", ("expensive", "trop cher", "cher", "ghali", "ghalia", "pricey", "discount", "réduction",
                         "reduction", "promo", "too much", "coupon")),
    ("purchase_intent", ("enroll", "buy", "inscrire", "acheter", "payment link", "lien de paiement", "nechri",
                         "nkhallas", "how can i pay", "comment payer", "sign up", "register", "ready to",
                         "je prends", "i'll take")),
]
OBJECTION_RULES: dict[str, tuple[str, ...]] = {
    "price": ("expensive", "cher", "ghali", "ghalia", "pricey", "discount", "too much", "réduction", "budget", "afford"),
    "time": ("full time", "much time", "pas beaucoup de temps", "no time", "busy", "wa9t", "temps"),
    "difficulty": ("the level", "never coded", "difficile", "difficult", "too hard", "beginner myself", "niveau"),
    "trust": ("certificate", "certificat", "recognized", "reconnu", "heard of you", "scam", "trust", "arnaque"),
}
POSITIVE = ("great", "perfect", "parfait", "merci beaucoup", "thank you", "behi barcha", "ya3tik", "excellent",
            "love", "super", "awesome", "génial", "sounds good")
NEGATIVE = ("frustrating", "frustrated", "frustrant", "déçu", "decu", "not normal", "pas normal", "mouch normal", "terrible", "angry",
            "stop sending", "expected better", "declined", "échoué", "can't", "cannot", "n'arrive pas",
            "not interested", "intéresse pas", "ma yhemnich", "ghalia barcha", "trop cher")


NEUTRAL = ("think about it", "réfléchir", "nchouf", "maybe", "peut-être", "we'll see", "on verra")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("’", "'")
    return re.sub(r"\s+", " ", f" {text} ")


def has(t: str, kw: str) -> bool:
    """Whole-word / whole-phrase match (avoids 'ai' in 'paid', 'cher' in 'chercher')."""
    return re.search(rf"(?<!\w){re.escape(kw.strip())}(?!\w)", t) is not None


def detect_intent(text: str) -> str:
    t = norm(text)
    for intent, kws in INTENT_RULES:
        if any(has(t, k) for k in kws):
            return intent
    return "information_request"


def detect_objections(text: str) -> list[str]:
    t = norm(text)
    return [o for o, kws in OBJECTION_RULES.items() if any(has(t, k) for k in kws)]


def sentiment_score(texts: list[str]) -> float:
    """Simple lexicon score in [-1, 1]; the LAST message counts double (how the conversation ended)."""
    score, weight_total = 0.0, 0.0
    for i, raw in enumerate(texts):
        t = norm(raw)
        w = 2.0 if i == len(texts) - 1 else 1.0
        pos = sum(has(t, k) for k in POSITIVE)
        neg = sum(has(t, k) for k in NEGATIVE)
        if pos or neg:
            score += w * (pos - neg) / (pos + neg)
            weight_total += w
        elif any(has(t, k) for k in NEUTRAL):
            weight_total += w  # explicit neutral message pulls the score toward 0
    return round(score / weight_total, 2) if weight_total else 0.0


def sentiment_label(score: float) -> str:
    return "positive" if score > 0.35 else "negative" if score < -0.35 else "neutral"
