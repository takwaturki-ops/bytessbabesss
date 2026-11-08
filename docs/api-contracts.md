# Contrats d'API — SmartFin AI

Référence commune entre le service d'agents, le backend et les workflows n8n.

## Service d'agents — base `http://localhost:8001`

### GET /health

Public. Retourne l'état du service, le mode (`mock` / `live` / `fallback`) et le modèle.

### GET /docs` · GET /openapi.json

Public. Swagger / OpenAPI complet, importable dans n8n ou Postman.

### POST /workflow/purchase

Parcours d'achat complet avec les 5 agents.

### POST /agents/sales — Voice Sales Agent

Entrée : `customer_message`, `conversation_history[]`, `customer_id?`, `channel`.

Données (`data`) :
- `reply`
- `detected_intent` : `purchase_intent`, `information_request`, `price_objection`, `course_comparison`, `payment_issue`, `not_interested`, `support_request`
- `objection_type`
- `recommended_courses[]` : `{ course_id, title, price_tnd, level, duration_weeks, reason }`
- `next_action`, `purchase_intent_score`, `confidence`, `catalog_grounded`

### POST /agents/customer-intelligence — Customer Intelligence

Entrée : `turns[{ role: "customer" | "agent", text }]`, `conversation_id?`, `customer_id?`.

Données (`data`) :
- `primary_intent`, `needs[]`, `motivations[]`, `objections[]`
- `sentiment`, `sentiment_score` (-1 à 1)
- `interest_score`, `satisfaction_score` (0 à 100)
- `purchase_stage`, `mentioned_course_ids[]`, `recommended_follow_up`, `summary`, `confidence`

### POST /agents/fraud — Security & Fraud Detection

Entrée :
- `event{ transaction_id, order_id, customer_id, amount_tnd, timestamp, status, expected_amount_tnd, currency, signature_valid, ip_country, device_id, card_fingerprint... }`
- `history[]`
- `customer_context{ home_country, known_devices[] }`

Données (`data`) :
- `action` : `allow`, `block` ou `require_human_approval`
- `risk_score`, `risk_level`
- `flags[]`, `rule_hits[]`
- `explanation`, `alert_summary`
- `decided_by` : `deterministic_rules`, `llm_can_override: false`

### POST /agents/payment — Payment Agent

Entrée : `transaction_id`, `order_id`, `status`, `amount_tnd`, `expected_amount_tnd`, `currency`, `provider_reference`, `signature_valid`, `failure_reason`, etc.

Données (`data`) :
- `final_status` : `success`, `failed`, `pending` ou `requires_review`
- `payment_confirmed` : `true` seulement si toutes les preuves sont valides
- `evidence{}`, `review_reasons[]`
- `recommended_action` : `grant_access`, `retry_payment`, `wait_for_confirmation` ou `manual_review`
- `summary`, `customer_message`

### POST /agents/financial — Financial Data Analyst

Entrée : `question`, `split` (données simulées) ou `orders[] + transactions[]`.

Données (`data`) :
- `metrics{ gross_revenue_tnd, paid_orders, order_conversion_rate, payment_success_rate, average_order_value_tnd, revenue_by_course[], revenue_by_month[], failure_reasons{}, ... }`
- `insights[]`, `narrative`, `data_scope{...}`
- `calculation_engine` : `pandas`

### Authentification et codes HTTP

- Authentification : si `INTERNAL_API_KEY` est défini, chaque POST doit envoyer l'en-tête `X-API-Key`. Sinon, la réponse est `401`. `/health` et `/docs` restent publics.
- `200` : succès.
- `422` : entrée invalide, ou erreur métier renvoyée par l'agent.
- `401` : clé absente ou fausse.
- `404` : `/workflow/purchase` avec un cours inconnu.

### Format de sortie commun aux routes `/agents/*`

```json
{
  "agent": "fraud_agent",
  "status": "ok",
  "data": { "..." : "résultat propre à chaque agent, voir ci-dessous" },
  "errors": []
}
```

- `status` vaut `ok` ou `error`. En cas d'erreur, `data` vaut `null` et le détail est dans `errors`.
- `meta.mode` vaut `mock`, `live` ou `fallback`.
- `meta.decision_source` vaut `deterministic`, `llm` ou `hybrid`.

Extrait de `meta` :

```json
{
  "agent": "fraud_agent",
  "mode": "mock",
  "model": null,
  "llm_used": false,
  "llm_calls": 0,
  "input_tokens": 0,
  "output_tokens": 0,
  "latency_ms": 3,
  "decision_source": "deterministic",
  "data_source": "simulated",
  "guardrails_triggered": [],
  "warnings": [],
  "disclaimer": "Prototype output based on SIMULATED data..."
}
```

## Backend — base `http://localhost:4000/api/internal`

### GET /kpis

Récupérer les KPI financiers (transactions, volumes, taux de fraude...).

### GET /alerts

Récupérer les alertes de fraude et de risque.

### POST /alerts

Créer une nouvelle alerte.

### GET /validations/pending

Récupérer les opérations en attente de validation humaine.

### POST /validations/:id/approve

Approuver une opération.

### POST /validations/:id/reject

Rejeter une opération.

### Besoins du service d'agents vis-à-vis du backend

- **Fraude** : les transactions récentes du client à envoyer dans `history` (ou `previous_transactions` de `/workflow/purchase`). Sans historique, les vrais doublons ne sont pas détectés.
- **Validation humaine** : quand le statut est `awaiting_human_approval` ou `requires_review`, le backend doit stocker l'alerte et exposer les routes d'approbation / rejet.
- **KPI** : si le backend calcule les KPI en SQL, il peut envoyer `orders[]` et `transactions[]` à `/agents/financial`, qui fera l'analyse et le texte d'explication.
