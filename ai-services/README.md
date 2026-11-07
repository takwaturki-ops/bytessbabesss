# 9antra AI Services: five agents + purchase workflow (FastAPI, port 8001)

Python service of the 9antra (قنطرة) FinTech project. Five specialised AI agents collaborate in one
**purchase workflow**: from the customer's first message to fraud screening, payment validation and the
financial update.

> **Everything here is SIMULATED**: course catalog, prices, customers, conversations, orders, payments and
> fraud cases. No real money moves and no banking data is collected.

## 1. Where this fits in the project

```
React (5173) --HTTP--> Node.js API (4000) --HTTP + X-API-Key--> ai-services (8001)   <- this folder
                            |
                            +--SQL--> PostgreSQL     (Node owns the database; agents never read it)
```

Node.js calls this service. The service returns structured JSON. Node stores orders and transactions and can
send a customer's recent transactions back in `previous_transactions`, so fraud checks see real history.

## 2. The five agents

| Agent | Responsibility | Decides with | LLM writes |
|---|---|---|---|
| **Voice Sales Agent** (`agents/sales_agent.py`) | understands the request, recommends catalog courses with real prices | catalog retrieval + price verification | the reply |
| **Customer Intelligence** (`agents/customer_intel_agent.py`) | needs, motivations, objections, sentiment, interest | catalog-ID filter, score clamping | the insights |
| **Security & Fraud** (`agents/fraud_agent.py`) | duplicates, repeated attempts, amount mismatch, bad signature, geo, velocity... | **10 Python rules: allow / block / require_human_approval** | explanation only |
| **Payment Agent** (`agents/payment_agent.py`) | validates the provider event and its evidence | **Python rules: success / failed / pending / requires_review** | summary only |
| **Financial Data Analyst** (`agents/financial_agent.py`) | revenue, conversion, payment statistics | **pandas** | narrative (numbers verified) |

The LLM can **never** change a fraud or payment decision. Those fields are not even in the LLM's output schema.
A payment is confirmed only with a success status, provider reference, valid signature, exact amount and TND currency.

## 3. The purchase workflow (`workflow/purchase.py`)

```
POST /workflow/purchase
   │
   ├─1 Sales Agent ............ message -> intent + recommended catalog course + real price
   ├─2 Customer Intelligence .. conversation -> needs, sentiment, objections, interest
   ├─3 Order creation ......... only if confirm_purchase=true; course & amount FROM THE CATALOG
   │                            -> order_id, transaction_id (all derived from workflow_id)
   ├─4 Fraud Agent ............ screens the payment event + history
   │       block ──────────────► STOP  final_status = blocked_by_fraud        (payment NOT processed)
   │       human approval ─────► STOP  final_status = awaiting_human_approval (payment NOT processed)
   ├─5 Payment Agent .......... success / failed / pending / requires_review
   ├─6 Financial Analyst ...... pandas: simulated baseline + this order; revenue counted ONLY if paid
   └─7 Response ............... all agent results + IDs + final_status + execution_trace
```

How the agents communicate: each one receives the previous step's output as **validated JSON**. For example, the
order creation step hands the fraud agent:

```json
{"event": {"transaction_id": "TXN-DEMO0001-1", "order_id": "ORD-DEMO0001", "customer_id": "CUST0007",
           "course_id": "C003", "amount_tnd": 349.0, "expected_amount_tnd": 349.0, "status": "success",
           "provider_reference": "PSIM-TXN-DEMO0001-1", "signature_valid": true, "ip_country": "TN", "...": "..."},
 "history": [], "customer_context": {"customer_id": "CUST0007", "home_country": "TN", "known_devices": ["..."]}}
```

The fraud agent answers `{"action": "allow", "risk_score": 0, "flags": []}`. Only then does the orchestrator
pass the same event to the payment agent.

| `payment_scenario` | Fraud | Payment | `final_status` | Revenue counted |
|---|---|---|---|---|
| `success` | allow | success | `completed` | yes |
| `failed` | allow | failed | `payment_failed` | no |
| `pending` | allow | pending | `payment_pending` | no |
| `amount_mismatch` | require_human_approval | not processed | `awaiting_human_approval` | no |
| `repeated_attempts` (3 fails) | require_human_approval | not processed | `awaiting_human_approval` | no |
| `suspicious_location` | require_human_approval | not processed | `awaiting_human_approval` | no |
| `duplicate` | block | not processed | `blocked_by_fraud` | no |
| `excessive_attempts` (6 fails) | block | not processed | `blocked_by_fraud` | no |
| `invalid_signature` | block | not processed | `blocked_by_fraud` | no |
| `confirm_purchase=false` or "not interested" | - | - | `no_purchase` | - |
| unknown `course_id` | - | - | `unknown_course` (HTTP 404) | - |

## 4. API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | status, mode (`mock`/`live`), model |
| GET | `/docs` | interactive Swagger documentation |
| POST | `/workflow/purchase` | **complete five-agent purchase journey** |
| POST | `/agents/sales`, `/agents/customer-intelligence`, `/agents/fraud`, `/agents/payment`, `/agents/financial` | one agent at a time |

Status codes: **200** for every business outcome (including blocked, failed, pending), **404** unknown course,
**422** invalid request, **401** wrong/missing `X-API-Key` (only when `INTERNAL_API_KEY` is set),
**500** internal error. Every body is structured JSON.

**Request**

```json
POST /workflow/purchase
{
  "customer_id": "CUST0007",
  "message": "I want to learn machine learning",
  "course_id": "C003",
  "payment_scenario": "success"
}
```

Optional fields: `confirm_purchase` (default `true`), `payment_method`, `discount_code` (`WELCOME10`,
`STUDENT20`, `HACK15`), `conversation_history`, `previous_transactions`, `workflow_id` (for reproducible demos).

**Response (shortened, real output in mock mode)**

```json
{
  "workflow_id": "WF-E453EB5863", "customer_id": "CUST0007",
  "order_id": "ORD-E453EB5863", "transaction_id": "TXN-E453EB5863-1",
  "course": {"course_id": "C003", "title": "Machine Learning Essentials", "price_tnd": 349.0},
  "amount_tnd": 349.0, "final_status": "completed", "purchase_confirmed": true,
  "next_step": "grant_course_access",
  "sales_agent_result": {"status": "ok", "data": {"detected_intent": "information_request", "...": "..."}, "meta": {"mode": "mock"}},
  "customer_intelligence_result": {"...": "..."}, "fraud_agent_result": {"...": "..."},
  "payment_agent_result": {"...": "..."}, "financial_analyst_result": {"...": "..."},
  "financial_impact": {"revenue_before_tnd": 21004.3, "revenue_after_tnd": 21353.3,
                       "revenue_delta_tnd": 349.0, "counted_as_revenue": true},
  "execution_trace": [
    {"step": 1, "name": "Sales conversation", "status": "ok", "decision": "information_request"},
    {"step": 2, "name": "Customer insights", "status": "ok", "decision": "awareness"},
    {"step": 3, "name": "Order creation", "status": "ok", "decision": "order_created"},
    {"step": 4, "name": "Fraud screening", "status": "ok", "decision": "allow"},
    {"step": 5, "name": "Payment validation", "status": "ok", "decision": "success"},
    {"step": 6, "name": "Financial update", "status": "ok", "decision": "revenue_counted"}
  ],
  "warnings": [], "errors": [], "llm_mode": "mock",
  "data_notice": "SIMULATED data and payments - no real money is moved."
}
```

The example in the brief mentioned a 250 TND course. The service always uses the catalog price, and the
simulated catalog lists *Machine Learning Essentials* (C003) at **349 TND**.

## 5. Install and run (Windows / PowerShell, from `ai-services/`)

```powershell
uv venv --python 3.12 .venv                                   # or: python -m venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
copy .env.example .env                                        # optional: mock mode works without it
.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

Then open http://localhost:8001/health and http://localhost:8001/docs.

```powershell
.venv\Scripts\python.exe -m pytest                 # 215 tests (agents, data, workflow, API) - mock only
.venv\Scripts\python.exe main.py eval              # 74 agent scenarios -> reports/eval_report.md
.venv\Scripts\python.exe main.py workflow-demo     # jury demo: full journey + every payment scenario
.venv\Scripts\python.exe main.py demo              # the five agents individually
```

## 6. Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_MODE` | `mock` | `mock` = no API calls (text labelled `[MOCK]`); `live` = real Claude calls |
| `LLM_MODEL` | `sonnet` | `sonnet` (claude-sonnet-5-5), `haiku` (cheapest), `opus` (upgrade) or a full model id |
| `LLM_API_KEY` / `ANTHROPIC_API_KEY` | - | needed only in live mode |
| `INTERNAL_API_KEY` | empty | when set, POST endpoints require header `X-API-Key` (shared with Node.js) |
| `LLM_EFFORT`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_S`, `LLM_MAX_RETRIES` | low, 1500, 45, 2 | cost / latency limits |

Every response says where its text came from: `meta.mode` is `mock`, `live`, or `fallback`. In `fallback`, a
live call failed and deterministic text was used, marked `[FALLBACK]` with the reason in `warnings`. Decisions
(fraud, payment, numbers) are identical in every mode because Python computes them.

## 7. Folder structure

```
ai-services/
├── api/main.py            FastAPI routes only (HTTP, status codes, X-API-Key)
├── workflow/              purchase orchestrator + request/response schemas
├── agents/                the five agents (BaseAgent subclasses)
├── core/                  config, shared LLM client (mock/live), BaseAgent, data access
├── schemas/               Pydantic input/output schemas per agent
├── prompts/               one concise system prompt per agent
├── tools/                 deterministic logic: fraud rules, payment rules, pandas metrics, catalog search
├── data/synthetic/        SIMULATED datasets (dev / eval split) + MANIFEST
├── data_generation/       seeded generators + validator  (python main.py generate | validate)
├── evaluation/            74 scenarios, check engine, reference calculations, report runner
├── examples/              demo_all_agents.py, demo_purchase_workflow.py
├── reports/               evaluation report (mock mode)
└── tests/                 pytest: agents, data, workflow, API
```

## 8. Test results (mock mode, 2026-11-08)

- **215/215 pytest tests pass**: the 174 original agent tests plus 41 new workflow and API tests covering
  success, failed, pending, duplicate, amount mismatch, repeated and excessive attempts, invalid signature,
  suspicious location, unknown course, customer declines, invalid input, ID consistency, LLM-cannot-override-fraud,
  no-revenue-unless-paid, status codes and API-key enforcement.
- **74/74 evaluation scenarios pass.** Fraud and payment accuracy are 100% on simulated cases.
- The service was started with uvicorn on port 8001 and checked over real HTTP (health, docs, workflow, 404, 422).

## 9. Limits and next steps

- **Live mode (real Claude) has not been tested yet**; no API key was available. Mock text is templated.
- Intent detection in mock mode is keyword-based. "I want to learn machine learning" is read as an information
  request, so the purchase relies on the explicit `course_id` + `confirm_purchase` (the "Buy" button).
- Human approval is returned as a status (`awaiting_human_approval`). The approve/reject screen and the
  persistence of orders belong to the Node.js backend and React frontend.
- Not implemented here: Business Strategy agent, prompt-injection filter, n8n workflows, real payments.
