# 9antra AI Agents - Evaluation Report

Generated: 2026-11-08 00:21 UTC  
**MOCK MODE - no LLM was called; text fields are deterministic templates labelled [MOCK]. Scores measure the deterministic rules + heuristic baseline, not Claude.**  
All data is SIMULATED.

## Summary: 74/74 scenarios passed

| Agent | Passed | Total |
|---|---|---|
| sales | 15 | 15 |
| customer_intel | 14 | 14 |
| payment | 16 | 16 |
| financial | 13 | 13 |
| fraud | 16 | 16 |

## Dataset-level metrics

```json
{
  "fraud": {
    "n": 50,
    "action_accuracy": 1.0,
    "expected_flags_found": 1.0,
    "false_positive_rate": 0.0,
    "false_negative_rate": 0.0,
    "confusion": {
      "tp": 20,
      "fp": 0,
      "tn": 30,
      "fn": 0
    },
    "mismatches": []
  },
  "payment": {
    "n": 23,
    "status_accuracy": 1.0,
    "unsafe_confirmations": 0
  },
  "customer_intel": {
    "n": 30,
    "intent_accuracy": 1.0,
    "sentiment_accuracy": 0.9667,
    "objection_exact_match": 1.0,
    "interest_mae": 3.6
  },
  "sales": {
    "n": 30,
    "intent_accuracy": 1.0,
    "recommendation_hit_rate": 1.0,
    "intent_errors": {}
  },
  "financial": {
    "cross_checks": [
      {
        "split": "dev",
        "fields_checked": 12,
        "mismatches": {}
      },
      {
        "split": "eval",
        "fields_checked": 12,
        "mismatches": {}
      },
      {
        "split": "all",
        "fields_checked": 12,
        "mismatches": {}
      }
    ],
    "all_match": true
  }
}
```

## sales

| ID | Category | Scenario | Mode | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| S01 | normal | Purchase intent (EN) | mock | status eq "ok"; data.detected_intent eq "purchase_intent"; data.next_action eq "send_payment_link"; data.recommended_courses[*].course_id contains "C002"; data.reply regex_present "199"; data.catalog_grounded eq true | "ok"; "purchase_intent"; "send_payment_link"; ["C002"]; "[MOCK] Excellent choice! Python for AI (199 TND, 4 weeks, b; true | PASS |
| S02 | normal | Information request | mock | status eq "ok"; data.detected_intent eq "information_request"; data.recommended_courses[*].course_id contains_any ["C003"] | "ok"; "information_request"; ["C003"] | PASS |
| S03 | normal | Price objection from a student | mock | status eq "ok"; data.detected_intent eq "price_objection"; data.objection_type eq "price"; data.next_action eq "handle_objection"; data.catalog_grounded eq true | "ok"; "price_objection"; "price"; "handle_objection"; true | PASS |
| S04 | normal | Course comparison | mock | status eq "ok"; data.detected_intent eq "course_comparison"; data.recommended_courses[*].course_id contains_all ["C003", "C004"] | "ok"; "course_comparison"; ["C003", "C004"] | PASS |
| S05 | normal | Payment issue is routed, no upsell | mock | status eq "ok"; data.detected_intent eq "payment_issue"; data.next_action eq "route_to_payment_support"; data.recommended_courses len_eq 0 | "ok"; "payment_issue"; "route_to_payment_support"; [] | PASS |
| S06 | normal | Support request | mock | status eq "ok"; data.detected_intent eq "support_request"; data.next_action eq "route_to_customer_support" | "ok"; "support_request"; "route_to_customer_support" | PASS |
| S07 | normal | Not interested | mock | status eq "ok"; data.detected_intent eq "not_interested"; data.next_action eq "end_conversation" | "ok"; "not_interested"; "end_conversation" | PASS |
| S08 | normal | Purchase intent (FR) | mock | status eq "ok"; data.detected_intent eq "purchase_intent"; data.recommended_courses[*].course_id contains "C009" | "ok"; "purchase_intent"; ["C009"] | PASS |
| S09 | normal | Information request (darija) | mock | status eq "ok"; data.detected_intent eq "information_request"; data.recommended_courses[*].course_id contains "C008" | "ok"; "information_request"; ["C008"] | PASS |
| S10 | edge | Difficulty objection -> beginner course | mock | status eq "ok"; data.objection_type eq "difficulty"; data.recommended_courses[*].level subset ["beginner"]; data.recommended_courses len_gte 1 | "ok"; "difficulty"; ["beginner"]; [{"course_id": "C007", "title": "Data Analysis with AI", "pr | PASS |
| S11 | missing_input | Empty message | mock | status eq "error"; errors contains "invalid_input" | "error"; ["invalid_input", "customer_message: String should have at l | PASS |
| S12 | invalid_output | LLM hallucinates a price and a course | scripted | status eq "ok"; data.catalog_grounded eq false; data.reply regex_absent "(?<!\\d)99 TND"; data.recommended_courses[*].course_id not_contains "C999"; meta.guardrails_triggered len_gte 1 | "ok"; false; "[FALLBACK] Here is what I recommend: Python for AI (199 TND; ["C002"]; ["unknown_course_id_removed", "reply_replaced:non_catalog_pr | PASS |
| S13 | invalid_output | LLM claims payment is done | scripted | status eq "ok"; data.reply regex_absent "payment (is/was) confirmed"; data.catalog_grounded eq false | "ok"; "[FALLBACK] Excellent choice! Python for AI (199 TND, 4 week; false | PASS |
| S14 | ambiguous | Bare greeting | mock | status eq "ok"; data.detected_intent eq "information_request"; data.next_action in ["present_courses", "answer_question"] | "ok"; "information_request"; "present_courses" | PASS |
| S15 | edge | Unknown customer id still answers | mock | status eq "ok"; meta.warnings contains "unknown_customer_id:CUST9999" | "ok"; ["unknown_customer_id:CUST9999"] | PASS |

## customer_intel

| ID | Category | Scenario | Mode | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| I01 | normal | Happy buyer | mock | status eq "ok"; data.primary_intent eq "purchase_intent"; data.sentiment eq "positive"; data.purchase_stage eq "decision"; data.interest_score gte 80; data.mentioned_course_ids contains "C002" | "ok"; "purchase_intent"; "positive"; "decision"; 90; ["C002"] | PASS |
| I02 | normal | Price objection, disappointed (FR) | mock | status eq "ok"; data.primary_intent eq "price_objection"; data.objections contains "price"; data.sentiment eq "negative" | "ok"; "price_objection"; ["price"]; "negative" | PASS |
| I03 | normal | Time objection, undecided | mock | status eq "ok"; data.primary_intent eq "information_request"; data.objections contains "time"; data.sentiment eq "neutral" | "ok"; "information_request"; ["time"]; "neutral" | PASS |
| I04 | normal | Trust objection | mock | status eq "ok"; data.objections contains "trust" | "ok"; ["trust"] | PASS |
| I05 | normal | Payment problem | mock | status eq "ok"; data.primary_intent eq "payment_issue"; data.purchase_stage eq "support"; data.sentiment eq "negative" | "ok"; "payment_issue"; "support"; "negative" | PASS |
| I06 | normal | Lost lead | mock | status eq "ok"; data.primary_intent eq "not_interested"; data.purchase_stage eq "lost"; data.interest_score lte 20 | "ok"; "not_interested"; "lost"; 0 | PASS |
| I07 | normal | Support request | mock | status eq "ok"; data.primary_intent eq "support_request"; data.mentioned_course_ids contains "C007" | "ok"; "support_request"; ["C007"] | PASS |
| I08 | normal | Darija happy buyer | mock | status eq "ok"; data.primary_intent eq "purchase_intent"; data.sentiment eq "positive"; data.mentioned_course_ids contains "C008" | "ok"; "purchase_intent"; "positive"; ["C008"] | PASS |
| I09 | edge | Multiple objections | mock | status eq "ok"; data.objections contains_all ["price", "difficulty"] | "ok"; ["price", "difficulty"] | PASS |
| I10 | missing_input | No turns | mock | status eq "error"; errors contains "invalid_input" | "error"; ["invalid_input", "turns: List should have at least 1 item a | PASS |
| I11 | missing_input | Only agent turns | mock | status eq "error"; errors contains "invalid_input" | "error"; ["invalid_input", "turns: Value error, at least one customer | PASS |
| I12 | invalid_output | LLM returns unknown course and out-of-range score | scripted | status eq "ok"; data.mentioned_course_ids eq ["C001"]; data.interest_score eq 100; meta.guardrails_triggered contains_all ["unknown_course_id_removed", "scores_clamped"] | "ok"; ["C001"]; 100; ["unknown_course_id_removed", "scores_clamped"] | PASS |
| I13 | invalid_output | LLM outage -> heuristic fallback | fallback | status eq "ok"; meta.mode eq "fallback"; data.summary startswith "[FALLBACK]"; data.primary_intent eq "purchase_intent" | "ok"; "fallback"; "[FALLBACK] Customer intent: purchase intent; sentiment neut; "purchase_intent" | PASS |
| I14 | ambiguous | Mixed signals | mock | status eq "ok"; data.sentiment eq "neutral"; data.objections contains "price" | "ok"; "neutral"; ["price"] | PASS |

## payment

| ID | Category | Scenario | Mode | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| P01 | normal | Success with full evidence | mock | status eq "ok"; data.final_status eq "success"; data.payment_confirmed eq true; data.recommended_action eq "grant_access" | "ok"; "success"; true; "grant_access" | PASS |
| P02 | normal | Card declined | mock | status eq "ok"; data.final_status eq "failed"; data.payment_confirmed eq false; data.recommended_action eq "retry_payment" | "ok"; "failed"; false; "retry_payment" | PASS |
| P03 | normal | Pending at provider | mock | status eq "ok"; data.final_status eq "pending"; data.recommended_action eq "wait_for_confirmation" | "ok"; "pending"; "wait_for_confirmation" | PASS |
| P04 | normal | Provider flagged for review | mock | status eq "ok"; data.final_status eq "requires_review"; data.recommended_action eq "manual_review" | "ok"; "requires_review"; "manual_review" | PASS |
| P05 | edge | Success claimed without provider reference | mock | status eq "ok"; data.final_status eq "requires_review"; data.payment_confirmed eq false; data.review_reasons contains "missing_provider_reference" | "ok"; "requires_review"; false; ["missing_provider_reference"] | PASS |
| P06 | edge | Success claimed with invalid signature | mock | status eq "ok"; data.final_status eq "requires_review"; data.review_reasons contains "signature_invalid_or_missing" | "ok"; "requires_review"; ["signature_invalid_or_missing"] | PASS |
| P07 | edge | Success with amount lower than expected | mock | status eq "ok"; data.final_status eq "requires_review"; data.review_reasons contains "amount_mismatch" | "ok"; "requires_review"; ["amount_mismatch"] | PASS |
| P08 | edge | Success in wrong currency | mock | status eq "ok"; data.final_status eq "requires_review"; data.review_reasons contains "currency_not_tnd" | "ok"; "requires_review"; ["currency_not_tnd"] | PASS |
| P09 | ambiguous | Provider alias 'authorized' means pending | mock | status eq "ok"; data.final_status eq "pending" | "ok"; "pending" | PASS |
| P10 | ambiguous | Unknown provider status | mock | status eq "ok"; data.final_status eq "requires_review"; data.payment_confirmed eq false; data.review_reasons[0] startswith "unknown_status" | "ok"; "requires_review"; false; "unknown_status:weird_state" | PASS |
| P11 | missing_input | Missing order_id | mock | status eq "error"; errors contains "invalid_input" | "error"; ["invalid_input", "order_id: Field required"] | PASS |
| P12 | missing_input | Success but expected amount unknown | mock | status eq "ok"; data.final_status eq "requires_review"; data.review_reasons contains "amount_or_expected_amount_missing" | "ok"; "requires_review"; ["amount_or_expected_amount_missing"] | PASS |
| P13 | invalid_output | LLM claims success on a pending payment | scripted | status eq "ok"; data.final_status eq "pending"; data.payment_confirmed eq false; meta.guardrails_triggered contains "unverified_success_claim_removed"; data.customer_message regex_absent "successful/confirmed/confirmé" | "ok"; "pending"; false; ["unverified_success_claim_removed"]; "Votre paiement est en cours de traitement. Nous vous confir | PASS |
| P14 | invalid_output | LLM outage falls back to deterministic text | fallback | status eq "ok"; data.final_status eq "success"; meta.mode eq "fallback"; data.summary startswith "[FALLBACK]" | "ok"; "success"; "fallback"; "[FALLBACK] Payment TXN-E1 for order ORD-E1 confirmed: 199.0 | PASS |
| P15 | ambiguous | Upper-case alias PAID with full evidence | mock | status eq "ok"; data.final_status eq "success"; data.payment_confirmed eq true | "ok"; "success"; true | PASS |
| P16 | edge | Zero amount on a pending event | mock | status eq "ok"; data.final_status eq "requires_review"; data.review_reasons contains "invalid_amount" | "ok"; "requires_review"; ["invalid_amount"] | PASS |

## financial

| ID | Category | Scenario | Mode | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| FA01 | normal | Overview on a known mini-dataset | mock | status eq "ok"; data.metrics.gross_revenue_tnd eq 457.2; data.metrics.paid_orders eq 3; data.metrics.total_orders eq 6 | "ok"; 457.2; 3; 6 | PASS |
| FA02 | normal | Average order value and discount total | mock | status eq "ok"; data.metrics.average_order_value_tnd eq 152.4; data.metrics.discount_total_tnd eq 39.8 | "ok"; 152.4; 39.8 | PASS |
| FA03 | normal | Payment statistics | mock | status eq "ok"; data.metrics.payment_success_rate eq 0.375; data.metrics.first_attempt_success_rate eq 0.3333; data.metrics.order_conversion_rate eq 0.5 | "ok"; 0.375; 0.3333; 0.5 | PASS |
| FA04 | normal | Best-selling course | mock | status eq "ok"; data.metrics.revenue_by_course[0].key eq "C001"; data.metrics.revenue_by_course[0].revenue_tnd eq 298.0 | "ok"; "C001"; 298.0 | PASS |
| FA05 | edge | Date filter on October only | mock | status eq "ok"; data.metrics.total_orders eq 3; data.metrics.gross_revenue_tnd eq 149.0; data.metrics.paid_orders eq 1 | "ok"; 3; 149.0; 1 | PASS |
| FA06 | edge | Empty dataset | mock | status eq "ok"; data.metrics.total_orders eq 0; data.metrics.gross_revenue_tnd eq 0.0; data.metrics.average_order_value_tnd eq 0.0; data.metrics.payment_success_rate eq 0.0 | "ok"; 0; 0.0; 0.0; 0.0 | PASS |
| FA07 | missing_input | Orders missing required column | mock | status eq "error"; errors[0] regex_present "missing columns" | "error"; "internal_error: ValueError: orders missing columns: ['cours | PASS |
| FA08 | invalid_output | LLM invents a revenue figure | scripted | status eq "ok"; data.narrative regex_absent "999999"; meta.guardrails_triggered[0] startswith "unverified_numbers_replaced" | "ok"; "3 of 6 orders were paid, generating 457.2 TND (average orde; "unverified_numbers_replaced:999999" | PASS |
| FA09 | normal | Dev split matches independent calculation | mock | status eq "ok"; data.metrics.total_orders eq 80; data.metrics.paid_orders eq 64; data.metrics.gross_revenue_tnd eq 21004.3; data.metrics.average_order_value_tnd eq 328.19; data.metrics.order_conversion_rate eq 0.8; data.metrics.total_transactions eq 92; data.metrics.successful_transactions eq 64; data.metrics.failed_transactions eq 18; data.metrics.payment_success_rate eq 0.6957; data.metrics.first_attempt_success_rate eq 0.7; data.metrics.pending_amount_tnd eq 1335.0; data.metrics.at_risk_amount_tnd eq 1859.4 | "ok"; 80; 64; 21004.3; 328.19; 0.8; 92; 64; 18; 0.6957; 0.7; 1335.0; 1859.4 | PASS |
| FA10 | normal | Eval split matches independent calculation | mock | status eq "ok"; data.metrics.total_orders eq 20; data.metrics.paid_orders eq 16; data.metrics.gross_revenue_tnd eq 5724.15; data.metrics.average_order_value_tnd eq 357.76; data.metrics.order_conversion_rate eq 0.8; data.metrics.total_transactions eq 23; data.metrics.successful_transactions eq 16; data.metrics.failed_transactions eq 4; data.metrics.payment_success_rate eq 0.6957; data.metrics.first_attempt_success_rate eq 0.7; data.metrics.pending_amount_tnd eq 728.0; data.metrics.at_risk_amount_tnd eq 199.0 | "ok"; 20; 16; 5724.15; 357.76; 0.8; 23; 16; 4; 0.6957; 0.7; 728.0; 199.0 | PASS |
| FA11 | normal | Failure reasons breakdown | mock | status eq "ok"; data.metrics.failure_reasons.card_declined eq 2; data.metrics.failure_reasons.insufficient_funds eq 1 | "ok"; 2; 1 | PASS |
| FA12 | invalid_output | Valid LLM narrative is kept (no false guardrail) | scripted | status eq "ok"; meta.guardrails_triggered len_eq 0; data.narrative regex_present "457.2" | "ok"; []; "Revenue was 457.2 TND from 3 paid orders; conversion is 50% | PASS |
| FA13 | ambiguous | Date range with no data | mock | status eq "ok"; data.metrics.total_orders eq 0; data.metrics.gross_revenue_tnd eq 0.0 | "ok"; 0; 0.0 | PASS |

## fraud

| ID | Category | Scenario | Mode | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| F01 | normal | Single clean success | mock | status eq "ok"; data.action eq "allow"; data.flags len_eq 0; data.alert_summary is_null true | "ok"; "allow"; []; null | PASS |
| F02 | normal | Order already paid -> duplicate | mock | status eq "ok"; data.action eq "block"; data.flags contains "DUPLICATE_PAYMENT" | "ok"; "block"; ["DUPLICATE_PAYMENT"] | PASS |
| F03 | normal | 3 failed attempts in 10 min | mock | status eq "ok"; data.action eq "require_human_approval"; data.flags contains "REPEATED_ATTEMPTS" | "ok"; "require_human_approval"; ["REPEATED_ATTEMPTS"] | PASS |
| F04 | normal | 6 failed attempts -> block | mock | status eq "ok"; data.action eq "block"; data.flags contains "REPEATED_ATTEMPTS" | "ok"; "block"; ["REPEATED_ATTEMPTS"] | PASS |
| F05 | normal | Amount differs from catalog | mock | status eq "ok"; data.action eq "require_human_approval"; data.flags contains "AMOUNT_MISMATCH" | "ok"; "require_human_approval"; ["AMOUNT_MISMATCH"] | PASS |
| F06 | normal | Success with invalid provider signature | mock | status eq "ok"; data.action eq "block"; data.flags contains "INVALID_SIGNATURE" | "ok"; "block"; ["INVALID_SIGNATURE"] | PASS |
| F07 | normal | Foreign IP on unknown device | mock | status eq "ok"; data.action eq "require_human_approval"; data.flags contains "GEO_MISMATCH" | "ok"; "require_human_approval"; ["GEO_MISMATCH"] | PASS |
| F08 | edge | Foreign IP but known device (travelling customer) | mock | status eq "ok"; data.action eq "allow" | "ok"; "allow" | PASS |
| F09 | edge | Two failures then success (false-positive check) | mock | status eq "ok"; data.action eq "allow" | "ok"; "allow" | PASS |
| F10 | edge | Duplicate AND amount mismatch | mock | status eq "ok"; data.action eq "block"; data.flags contains_all ["DUPLICATE_PAYMENT", "AMOUNT_MISMATCH"]; data.risk_score gte 90 | "ok"; "block"; ["AMOUNT_MISMATCH", "DUPLICATE_PAYMENT"]; 100 | PASS |
| F11 | missing_input | Event without timestamp | mock | status eq "error"; errors contains "invalid_input" | "error"; ["invalid_input", "event.timestamp: Field required"] | PASS |
| F12 | invalid_output | LLM explanation tries to approve a blocked payment | scripted | status eq "ok"; data.action eq "block"; meta.guardrails_triggered contains "contradictory_explanation_replaced"; data.explanation regex_absent "safe to approve" | "ok"; "block"; ["contradictory_explanation_replaced"]; "Decision block (risk 70/100) because INVALID_SIGNATURE: pro | PASS |
| F13 | edge | Non-TND currency | mock | status eq "ok"; data.action eq "require_human_approval"; data.flags contains "CURRENCY_MISMATCH" | "ok"; "require_human_approval"; ["CURRENCY_MISMATCH"] | PASS |
| F14 | edge | Unusually high amount | mock | status eq "ok"; data.action eq "require_human_approval"; data.flags contains "HIGH_AMOUNT" | "ok"; "require_human_approval"; ["HIGH_AMOUNT"] | PASS |
| F15 | ambiguous | Five failures but 2 hours ago (outside window) | mock | status eq "ok"; data.action eq "allow" | "ok"; "allow" | PASS |
| F16 | edge | Zero amount | mock | status eq "ok"; data.action eq "block"; data.flags contains "INVALID_AMOUNT" | "ok"; "block"; ["INVALID_AMOUNT"] | PASS |
