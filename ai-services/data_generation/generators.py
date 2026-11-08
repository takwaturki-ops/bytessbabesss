"""Deterministic generators for SIMULATED 9antra datasets.

All people, conversations, orders, transactions and fraud cases produced here are
fictional. Every record carries `"simulated": True`.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta

from data_generation.catalog import COURSES, DISCOUNT_CODES

SEED = 42
BASE_DATE = datetime(2026, 9, 1, 8, 0, 0)
COURSE_BY_ID = {c["course_id"]: c for c in COURSES}

FIRST_NAMES = ["Amine", "Yasmine", "Mohamed", "Salma", "Youssef", "Rania", "Aziz", "Mariem", "Skander", "Ines",
               "Hamza", "Nour", "Khalil", "Eya", "Bilel", "Asma", "Omar", "Sarra", "Fares", "Chaima",
               "Walid", "Hiba", "Ahmed", "Oumaima", "Seif", "Rahma", "Mehdi", "Emna", "Anis", "Lina"]
LAST_NAMES = ["Ben Ali", "Trabelsi", "Jaziri", "Gharbi", "Mansouri", "Bouazizi", "Hammami", "Chebbi", "Ayari",
              "Sassi", "Kefi", "Dridi", "Mejri", "Belhaj", "Zouari", "Ferchichi", "Khelifi", "Haddad", "Toumi", "Jlassi"]
CITIES = ["Tunis", "Sfax", "Sousse", "Ariana", "Bizerte", "Nabeul", "Monastir", "Gabes", "Kairouan", "Ben Arous"]
SEGMENTS = {
    "student": ["Computer science student", "Engineering student", "Business student"],
    "professional": ["Software developer", "Accountant", "Data analyst", "Bank employee", "Teacher"],
    "entrepreneur": ["E-commerce founder", "Agency owner", "Freelancer"],
    "manager": ["IT manager", "Marketing manager", "Operations director"],
}
SEGMENT_INTERESTS = {
    "student": ["programming", "machine_learning", "foundations", "generative_ai", "data"],
    "professional": ["data", "generative_ai", "programming", "machine_learning", "engineering", "business"],
    "entrepreneur": ["business", "generative_ai", "data"],
    "manager": ["business", "foundations", "generative_ai"],
}
SEGMENT_BUDGET = {"student": (100, 300), "professional": (200, 600), "entrepreneur": (150, 500), "manager": (300, 800)}

INTENTS = ["purchase_intent", "information_request", "price_objection", "course_comparison",
           "payment_issue", "not_interested", "support_request"]
INTENT_WEIGHTS = [0.24, 0.24, 0.16, 0.10, 0.10, 0.08, 0.08]

TEMPLATES = {
    "purchase_intent": {
        "en": ["I want to enroll in the {title} course. How can I pay?",
               "I'm ready to buy {title}, please send me the payment link."],
        "fr": ["Je veux m'inscrire à la formation {title}. Comment payer ?",
               "Je suis prêt à acheter {title}, envoyez-moi le lien de paiement."],
        "darija": ["N7eb nechri formation {title}, kifech nkhallas?"],
    },
    "information_request": {
        "en": ["Can you tell me more about your {topic} courses? What will I learn?",
               "Do you have something about {topic}? How long does it take?"],
        "fr": ["Avez-vous une formation sur {topic} ? Quelle est la durée ?"],
        "darija": ["3andkom formation fi {topic}? 9addech todhher?"],
    },
    "price_objection": {
        "en": ["I'm interested in {title} but it's too expensive for me.",
               "Is there any discount on {title}? It's a bit pricey."],
        "fr": ["La formation {title} m'intéresse mais c'est trop cher."],
        "darija": ["{title} ya3jebni ama ghalia barcha."],
    },
    "course_comparison": {
        "en": ["What's the difference between {title} and {title2}? Which one should I take?"],
        "fr": ["Quelle est la différence entre {title} et {title2} ? Laquelle choisir ?"],
        "darija": ["Chnowa el far9 bin {title} w {title2}?"],
    },
    "payment_issue": {
        "en": ["I tried to pay for {title} but my card was declined.",
               "I paid for {title} but I still have no access, the payment says pending."],
        "fr": ["Mon paiement pour {title} a échoué, que faire ?"],
        "darija": ["Khallast {title} ama el paiement ma t3addech."],
    },
    "not_interested": {
        "en": ["Thanks but I'm not interested anymore.", "Please stop sending me messages."],
        "fr": ["Merci, mais ça ne m'intéresse pas."],
        "darija": ["Merci, ma yhemnich."],
    },
    "support_request": {
        "en": ["I bought {title} last week, how do I access the videos?", "I can't log in to my {title} course."],
        "fr": ["Je n'arrive pas à accéder à mon cours {title}."],
        "darija": ["Chrit {title} ama ma najemch nodkhol lel cours."],
    },
}
OBJECTION_FOLLOWUPS = {
    "price": ["Honestly it's too expensive for a student.", "C'est trop cher pour moi.", "Ghalia chwaya."],
    "time": ["I work full time, I don't have much time.", "Je n'ai pas beaucoup de temps."],
    "difficulty": ["I'm not sure I have the level, I've never coded.", "J'ai peur que ce soit trop difficile."],
    "trust": ["Is the certificate recognized? I've never heard of you before.", "Le certificat est-il reconnu ?"],
}
CLOSINGS = {
    "positive": ["Great, that sounds perfect, thank you!", "Parfait, merci beaucoup !", "Ya3tik essa7a, behi barcha!"],
    "neutral": ["OK, I'll think about it.", "D'accord, je vais réfléchir.", "Behi, nchouf."],
    "negative": ["This is frustrating, I expected better.", "Je suis déçu, ce n'est pas normal.", "Mouch normal hedha."],
}
INTENT_BASE_INTEREST = {"purchase_intent": 85, "course_comparison": 70, "information_request": 60,
                        "price_objection": 55, "payment_issue": 75, "support_request": 50, "not_interested": 10}
SENTIMENT_SATISFACTION = {"positive": 80, "neutral": 60, "negative": 30}


def _ts(rng: random.Random, max_days: int = 60) -> datetime:
    return BASE_DATE + timedelta(minutes=rng.randint(0, max_days * 24 * 60))


def _fingerprint(*parts: str) -> str:
    return "fp_" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]


def _pick_course(rng: random.Random, interests: list[str], budget: tuple[int, int] | None = None) -> dict:
    pool = [c for c in COURSES if c["category"] in interests] or COURSES
    if budget and rng.random() < 0.7:
        affordable = [c for c in pool if c["price_tnd"] <= budget[1]]
        pool = affordable or pool
    return rng.choice(pool)


# --------------------------------------------------------------------------- customers
def generate_customers(rng: random.Random, n: int = 100) -> list[dict]:
    customers = []
    for i in range(1, n + 1):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        segment = rng.choices(list(SEGMENTS), weights=[0.35, 0.35, 0.15, 0.15])[0]
        interests = rng.sample(SEGMENT_INTERESTS[segment], k=min(2, len(SEGMENT_INTERESTS[segment])))
        lo, hi = SEGMENT_BUDGET[segment]
        customers.append({
            "customer_id": f"CUST{i:04d}",
            "full_name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower().replace(' ', '')}{i}@example.com",
            "city": rng.choice(CITIES),
            "country": "TN",
            "age": rng.randint(19, 55) if segment != "student" else rng.randint(18, 26),
            "segment": segment,
            "occupation": rng.choice(SEGMENTS[segment]),
            "experience_level": rng.choices(["beginner", "intermediate", "advanced"], weights=[0.5, 0.35, 0.15])[0],
            "preferred_language": rng.choices(["fr", "ar", "en", "darija"], weights=[0.4, 0.2, 0.15, 0.25])[0],
            "interests": interests,
            "budget_min_tnd": lo,
            "budget_max_tnd": hi,
            "known_devices": [f"DEV-{i:04d}-A"] + ([f"DEV-{i:04d}-B"] if rng.random() < 0.3 else []),
            "signup_date": (BASE_DATE - timedelta(days=rng.randint(0, 365))).date().isoformat(),
            "simulated": True,
        })
    return customers


# --------------------------------------------------------------------------- conversations
def _lang_key(pref: str) -> str:
    return {"ar": "darija", "darija": "darija", "fr": "fr", "en": "en"}[pref]


def generate_conversations(rng: random.Random, customers: list[dict], n: int = 150) -> list[dict]:
    conversations = []
    for i in range(1, n + 1):
        cust = rng.choice(customers)
        intent = rng.choices(INTENTS, weights=INTENT_WEIGHTS)[0]
        course = _pick_course(rng, cust["interests"], (cust["budget_min_tnd"], cust["budget_max_tnd"]))
        alt = rng.choice([c for c in COURSES if c["category"] == course["category"] and c is not course] or COURSES)
        lang = _lang_key(cust["preferred_language"])
        if rng.random() < 0.25:
            lang = rng.choice(["en", "fr", "darija"])
        topic = course["keywords"][0]
        opener = rng.choice(TEMPLATES[intent][lang]).format(title=course["title"], topic=topic, title2=alt["title"])

        # Ground-truth labels
        objections: list[str] = []
        if intent == "price_objection":
            objections.append("price")
        if intent in ("information_request", "course_comparison", "purchase_intent", "price_objection") and rng.random() < 0.35:
            extra = rng.choice(["price", "time", "difficulty", "trust"])
            if extra not in objections:
                objections.append(extra)

        if intent in ("payment_issue", "support_request"):
            sentiment = rng.choices(["negative", "neutral"], weights=[0.7, 0.3])[0]
        elif intent == "not_interested":
            sentiment = rng.choices(["negative", "neutral"], weights=[0.5, 0.5])[0]
        elif intent == "purchase_intent":
            sentiment = rng.choices(["positive", "neutral"], weights=[0.8, 0.2])[0]
        elif objections:
            sentiment = rng.choices(["neutral", "negative", "positive"], weights=[0.6, 0.25, 0.15])[0]
        else:
            sentiment = rng.choices(["positive", "neutral"], weights=[0.6, 0.4])[0]

        turns = [{"role": "customer", "text": opener}]
        if intent not in ("not_interested",):
            turns.append({"role": "agent", "text": (
                f"{course['title']} costs {course['price_tnd']:.0f} TND and lasts {course['duration_weeks']} weeks "
                f"({course['duration_hours']}h, {course['format']}). {course['description']}")})
        for obj in objections:
            if obj == "price" and intent == "price_objection":
                continue  # already expressed in the opener
            turns.append({"role": "customer", "text": rng.choice(OBJECTION_FOLLOWUPS[obj])})
            turns.append({"role": "agent", "text": "I understand. Let me suggest an option that fits you better."})
        turns.append({"role": "customer", "text": rng.choice(CLOSINGS[sentiment])})

        interest = INTENT_BASE_INTEREST[intent] + rng.randint(-8, 8) + {"positive": 5, "neutral": 0, "negative": -10}[sentiment]
        satisfaction = SENTIMENT_SATISFACTION[sentiment] + rng.randint(-10, 10)
        if intent == "purchase_intent" and sentiment == "positive":
            outcome = "converted"
        elif intent == "not_interested":
            outcome = "lost"
        elif intent in ("payment_issue", "support_request"):
            outcome = "needs_support"
        else:
            outcome = rng.choices(["follow_up", "converted", "lost"], weights=[0.6, 0.2, 0.2])[0]

        conversations.append({
            "conversation_id": f"CONV{i:04d}",
            "customer_id": cust["customer_id"],
            "channel": rng.choices(["chat", "voice"], weights=[0.75, 0.25])[0],
            "language": lang,
            "started_at": _ts(rng).isoformat(),
            "turns": turns,
            "labels": {
                "intent": intent,
                "objections": objections,
                "sentiment": sentiment,
                "interest_score": max(0, min(100, interest)),
                "satisfaction_score": max(0, min(100, satisfaction)),
                "mentioned_course_id": None if intent == "not_interested" else course["course_id"],
                "outcome": outcome,
            },
            "simulated": True,
        })
    return conversations


# --------------------------------------------------------------------------- orders + transactions
PAYMENT_METHODS = ["card", "mobile_wallet", "bank_transfer"]
FAILURE_REASONS = ["insufficient_funds", "card_declined", "3ds_failed", "timeout", "expired_card"]


def generate_orders_and_transactions(rng: random.Random, customers: list[dict],
                                     conversations: list[dict], n: int = 100) -> tuple[list[dict], list[dict]]:
    converted = [c for c in conversations if c["labels"]["outcome"] in ("converted", "needs_support")
                 and c["labels"]["mentioned_course_id"]]
    orders, txns = [], []
    txn_counter = 1
    scenario_pool = (["success"] * 70 + ["retry_success"] * 10 + ["failed"] * 7 + ["pending"] * 7 + ["review"] * 6)
    rng.shuffle(scenario_pool)
    cust_by_id = {c["customer_id"]: c for c in customers}

    for i in range(1, n + 1):
        if converted and rng.random() < 0.4:
            conv = converted.pop(0)
            cust = cust_by_id[conv["customer_id"]]
            course = COURSE_BY_ID[conv["labels"]["mentioned_course_id"]]
            conv_id = conv["conversation_id"]
            created = datetime.fromisoformat(conv["started_at"]) + timedelta(minutes=rng.randint(5, 240))
        else:
            cust = rng.choice(customers)
            course = _pick_course(rng, cust["interests"])
            conv_id = None
            created = _ts(rng)
        code = rng.choice(list(DISCOUNT_CODES)) if rng.random() < 0.25 else None
        amount = round(course["price_tnd"] * (1 - DISCOUNT_CODES.get(code, 0.0)), 2)
        method = rng.choices(PAYMENT_METHODS, weights=[0.6, 0.3, 0.1])[0]
        device = rng.choice(cust["known_devices"])
        card_fp = _fingerprint(cust["customer_id"], "card1") if method == "card" else None
        scenario = scenario_pool[i - 1]
        order_id = f"ORD{i:04d}"

        def txn(attempt: int, status: str, minutes: int, **over) -> dict:
            nonlocal txn_counter
            rec = {
                "transaction_id": f"TXN{txn_counter:05d}", "order_id": order_id, "customer_id": cust["customer_id"],
                "attempt_no": attempt, "amount_tnd": amount, "expected_amount_tnd": amount, "currency": "TND",
                "payment_method": method, "status": status,
                "provider_reference": f"PSIM-{txn_counter:06d}" if status == "success" else None,
                "failure_reason": None, "signature_valid": True, "ip_country": "TN", "device_id": device,
                "card_fingerprint": card_fp,
                "created_at": (created + timedelta(minutes=minutes)).isoformat(), "simulated": True,
            }
            rec.update(over)
            txn_counter += 1
            return rec

        if scenario == "success":
            order_txns = [txn(1, "success", 1)]
            status = "paid"
        elif scenario == "retry_success":
            order_txns = [txn(1, "failed", 1, failure_reason=rng.choice(FAILURE_REASONS)), txn(2, "success", 4)]
            status = "paid"
        elif scenario == "failed":
            k = rng.randint(1, 3)
            order_txns = [txn(a, "failed", a * 3, failure_reason=rng.choice(FAILURE_REASONS)) for a in range(1, k + 1)]
            status = "failed"
        elif scenario == "pending":
            order_txns = [txn(1, "pending", 1)]
            status = "pending"
        else:  # review: either amount mismatch or invalid signature on a reported success
            if rng.random() < 0.5:
                order_txns = [txn(1, "requires_review", 1, amount_tnd=round(amount * rng.choice([0.5, 0.9, 1.2]), 2),
                                  failure_reason="amount_mismatch")]
            else:
                order_txns = [txn(1, "requires_review", 1, signature_valid=False, failure_reason="invalid_signature")]
            status = "requires_review"
        txns.extend(order_txns)
        orders.append({
            "order_id": order_id, "customer_id": cust["customer_id"], "course_id": course["course_id"],
            "conversation_id": conv_id, "list_price_tnd": course["price_tnd"], "discount_code": code,
            "amount_tnd": amount, "currency": "TND", "payment_method": method, "status": status,
            "created_at": created.isoformat(), "simulated": True,
        })
    return orders, txns


# --------------------------------------------------------------------------- fraud scenarios
def generate_fraud_scenarios(rng: random.Random, customers: list[dict]) -> list[dict]:
    plan = ([("normal_single_success", 14), ("normal_retry_after_failure", 6), ("normal_returning_customer", 4),
             ("normal_known_device_abroad", 3), ("normal_two_failures_then_attempt", 3),
             ("duplicate_payment", 4), ("repeated_attempts_moderate", 3), ("repeated_attempts_excessive", 2),
             ("amount_mismatch", 3), ("invalid_amount", 1), ("invalid_signature", 2), ("device_velocity", 2),
             ("geo_mismatch_new_device", 2), ("multiple_cards", 1)])
    expected = {
        "normal_single_success": ("normal", "allow", []),
        "normal_retry_after_failure": ("normal", "allow", []),
        "normal_returning_customer": ("normal", "allow", []),
        "normal_known_device_abroad": ("normal", "allow", []),
        "normal_two_failures_then_attempt": ("normal", "allow", []),
        "duplicate_payment": ("suspicious", "block", ["DUPLICATE_PAYMENT"]),
        "repeated_attempts_moderate": ("suspicious", "require_human_approval", ["REPEATED_ATTEMPTS"]),
        "repeated_attempts_excessive": ("suspicious", "block", ["REPEATED_ATTEMPTS"]),
        "amount_mismatch": ("suspicious", "require_human_approval", ["AMOUNT_MISMATCH"]),
        "invalid_amount": ("suspicious", "block", ["INVALID_AMOUNT"]),
        "invalid_signature": ("suspicious", "block", ["INVALID_SIGNATURE"]),
        "device_velocity": ("suspicious", "require_human_approval", ["DEVICE_VELOCITY"]),
        "geo_mismatch_new_device": ("suspicious", "require_human_approval", ["GEO_MISMATCH"]),
        "multiple_cards": ("suspicious", "require_human_approval", ["MULTIPLE_CARDS"]),
    }
    scenarios = []
    sid = 1
    for stype, count in plan:
        for _ in range(count):
            cust = rng.choice(customers)
            course = rng.choice(COURSES)
            t0 = _ts(rng)
            order_id = f"FORD{sid:03d}"
            dev = cust["known_devices"][0]
            fp = _fingerprint(cust["customer_id"], "card1")
            price = course["price_tnd"]

            def ev(minutes: int, status: str, **over) -> dict:
                rec = {"transaction_id": f"FTXN{sid:03d}-{minutes:03d}", "order_id": order_id,
                       "customer_id": cust["customer_id"], "course_id": course["course_id"],
                       "amount_tnd": price, "expected_amount_tnd": price, "currency": "TND",
                       "payment_method": "card", "status": status,
                       "provider_reference": "PSIM-F" + f"{sid:03d}{minutes:03d}" if status == "success" else None,
                       "signature_valid": True, "ip_country": "TN", "device_id": dev, "card_fingerprint": fp,
                       "timestamp": (t0 + timedelta(minutes=minutes)).isoformat()}
                rec.update(over)
                return rec

            history: list[dict] = []
            if stype == "normal_single_success":
                event = ev(0, "success")
            elif stype == "normal_retry_after_failure":
                history = [ev(0, "failed")]
                event = ev(3, "success")
            elif stype == "normal_returning_customer":
                other = rng.choice([c for c in COURSES if c is not course])
                history = [dict(ev(0, "success"), order_id=f"FORD{sid:03d}-OLD", course_id=other["course_id"],
                                amount_tnd=other["price_tnd"], expected_amount_tnd=other["price_tnd"],
                                timestamp=(t0 - timedelta(days=20)).isoformat())]
                event = ev(0, "success")
            elif stype == "normal_known_device_abroad":
                event = ev(0, "success", ip_country=rng.choice(["FR", "DE", "CA"]))
            elif stype == "normal_two_failures_then_attempt":
                history = [ev(0, "failed"), ev(4, "failed")]
                event = ev(9, "success")
            elif stype == "duplicate_payment":
                history = [ev(0, "success")]
                event = ev(rng.randint(1, 30), "success")
            elif stype == "repeated_attempts_moderate":
                k = rng.choice([3, 4])
                history = [ev(m * 3, "failed") for m in range(k)]
                event = ev(k * 3, "pending")
            elif stype == "repeated_attempts_excessive":
                k = rng.choice([5, 6, 7])
                history = [ev(m * 2, "failed") for m in range(k)]
                event = ev(k * 2, "pending")
            elif stype == "amount_mismatch":
                event = ev(0, "success", amount_tnd=round(price * rng.choice([0.5, 0.8, 1.3]), 2))
            elif stype == "invalid_amount":
                event = ev(0, "pending", amount_tnd=rng.choice([0.0, -10.0]))
            elif stype == "invalid_signature":
                event = ev(0, "success", signature_valid=False)
            elif stype == "device_velocity":
                history = [dict(ev(m * 2, "success"), order_id=f"FORD{sid:03d}-V{m}",
                                customer_id=rng.choice(customers)["customer_id"]) for m in range(4)]
                event = ev(9, "pending")
            elif stype == "geo_mismatch_new_device":
                event = ev(0, "pending", ip_country=rng.choice(["NG", "RU", "BR", "VN"]), device_id=f"DEV-UNKNOWN-{sid:03d}")
            else:  # multiple_cards
                history = [ev(m * 5, "failed", card_fingerprint=_fingerprint(cust["customer_id"], f"card{m + 2}"))
                           for m in range(2)]
                event = ev(12, "pending", card_fingerprint=_fingerprint(cust["customer_id"], "card9"))

            label, action, flags = expected[stype]
            scenarios.append({
                "scenario_id": f"FRD{sid:03d}", "scenario_type": stype, "label": label,
                "expected_action": action, "expected_flags": flags,
                "customer_context": {"customer_id": cust["customer_id"], "home_country": "TN",
                                     "known_devices": cust["known_devices"]},
                "event": event, "history": history, "simulated": True,
            })
            sid += 1
    rng.shuffle(scenarios)
    return scenarios
