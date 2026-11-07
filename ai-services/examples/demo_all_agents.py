"""Demo: the five 9antra agents working together on SIMULATED data.

Story: a customer chats with the sales agent -> customer intel analyses the chat -> the customer pays ->
the fraud agent screens the payment -> the payment agent interprets it -> the financial analyst reports.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import CustomerIntelAgent, FinancialAnalystAgent, FraudAgent, PaymentAgent, SalesAgent  # noqa: E402
from core import data  # noqa: E402
from core.llm_client import get_default_client  # noqa: E402


def show(title: str, resp, fields: list[str]) -> None:
    d = resp.model_dump()
    print(f"\n=== {title}  [status={d['status']} mode={d['meta']['mode']} llm_used={d['meta']['llm_used']}"
          f" guardrails={d['meta']['guardrails_triggered'] or '-'}]")
    if d["status"] != "ok":
        print("  errors:", d["errors"])
        return
    for f in fields:
        print(f"  {f}: {json.dumps(d['data'][f], ensure_ascii=False, default=str)}")


def main() -> None:
    llm = get_default_client()
    print("9antra AI agents demo - ALL DATA IS SIMULATED")
    print(f"LLM mode: {llm.mode}" + (f" | model: {llm.model}" if llm.model else " | no API calls ([MOCK] = templated text)"))

    customer = data.customer("CUST0007")
    sales, intel, fraud, payment, fin = (SalesAgent(llm), CustomerIntelAgent(llm), FraudAgent(llm),
                                         PaymentAgent(llm), FinancialAnalystAgent(llm))

    # 1. Sales conversation
    history = []
    for msg in ["Salut, avez-vous une formation sur machine learning ? Quelle est la durée ?",
                "C'est trop cher pour moi.",
                "Je veux m'inscrire à la formation Machine Learning Essentials. Comment payer ?"]:
        r = sales.run({"customer_message": msg, "conversation_history": history, "customer_id": customer["customer_id"]})
        show(f"SALES  <- {msg!r}", r, ["detected_intent", "objection_type", "next_action", "reply",
                                        "recommended_courses"])
        history += [{"role": "customer", "text": msg}, {"role": "agent", "text": r.data.reply}]

    # 2. Customer intelligence on the full conversation
    r = intel.run({"turns": history, "customer_id": customer["customer_id"], "conversation_id": "DEMO-CONV"})
    show("CUSTOMER INTEL", r, ["primary_intent", "objections", "sentiment", "interest_score", "purchase_stage",
                               "recommended_follow_up"])

    # 3. Payment events: the customer pays for C003 (349 TND). Fraud screening, then payment interpretation.
    price = data.course_map()["C003"]["price_tnd"]
    base = {"order_id": "DEMO-ORD-1", "customer_id": customer["customer_id"], "course_id": "C003",
            "amount_tnd": price, "expected_amount_tnd": price, "currency": "TND", "payment_method": "card",
            "signature_valid": True, "ip_country": "TN", "device_id": customer["known_devices"][0],
            "card_fingerprint": "fp_demo"}
    ok_event = {**base, "transaction_id": "DEMO-TXN-1", "status": "success", "provider_reference": "PSIM-DEMO-1",
                "timestamp": "2026-10-20T14:05:00"}
    dup_event = {**ok_event, "transaction_id": "DEMO-TXN-2", "provider_reference": "PSIM-DEMO-2",
                 "timestamp": "2026-10-20T14:07:00"}
    ctx = {"customer_id": customer["customer_id"], "home_country": "TN", "known_devices": customer["known_devices"]}

    r = fraud.run({"event": ok_event, "customer_context": ctx})
    show("FRAUD  first payment", r, ["action", "risk_score", "flags", "explanation"])
    r = payment.run(ok_event)
    show("PAYMENT first payment", r, ["final_status", "payment_confirmed", "recommended_action", "customer_message"])

    r = fraud.run({"event": dup_event, "history": [ok_event], "customer_context": ctx})
    show("FRAUD  second identical payment 2 min later", r, ["action", "risk_score", "flags", "alert_summary"])
    r = payment.run({**ok_event, "transaction_id": "DEMO-TXN-3", "signature_valid": False})
    show("PAYMENT 'success' with invalid signature", r, ["final_status", "payment_confirmed", "review_reasons"])

    # 4. Financial analysis of the simulated dev dataset
    r = fin.run({"question": "How are sales and payments doing?", "split": "dev"})
    show("FINANCIAL ANALYST", r, ["narrative", "insights"])
    m = r.data.metrics
    print(f"  key metrics: revenue={m.gross_revenue_tnd} TND, paid={m.paid_orders}/{m.total_orders}, "
          f"payment_success_rate={m.payment_success_rate}, AOV={m.average_order_value_tnd} TND")


if __name__ == "__main__":
    main()
