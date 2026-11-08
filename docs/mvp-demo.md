# 9antra MVP: run and demo

All payments and data are SIMULATED. No real money moves.

## Start (3 terminals)

**1. AI service** (port 8001)
```powershell
cd ai-services
.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```
(first time: `uv venv --python 3.12 .venv` then `uv pip install --python .venv\Scripts\python.exe -r requirements.txt`)

**2. Backend** (port 4000). Copy `backend/.env.example` to `backend/.env` and set `JWT_SECRET`.
- With Neon: set `DATABASE_URL`, run `npm run db:migrate`, then `npm run create-admin -- admin@9antra.tn <password> "Admin 9antra"`.
- Without Neon (local demo only): `USE_IN_MEMORY_DB=true` plus `DEMO_ADMIN_EMAIL` / `DEMO_ADMIN_PASSWORD`. Data is lost on restart.
```powershell
cd backend
npm install
npm start
```

**3. Frontend** (port 5173). Copy `frontend/.env.example` to `frontend/.env` and leave `VITE_API_BASE_URL` empty: the Vite dev server forwards `/api/*` to the backend, so everything is served from **one URL, http://localhost:5173**.
```powershell
cd frontend
npm install
npm run dev
```

Check: http://localhost:5173/api/health (proxied to the backend) shows `database`, `database_mode` and `ai_service`.

## Demo script
1. Open http://localhost:5173: the mascot greets you in Derja.
2. "Créer un compte" opens the learner space (`/app`).
3. Assistant IA: "Je veux apprendre le machine learning", then "C'est trop cher". The Sales Agent replies, and the history persists (reload, then reopen the conversation).
4. Click "Acheter" on a recommendation and choose a scenario:
   - "Paiement accepté": confirmed purchase, all 5 agents run.
   - "Signature invalide": blocked by fraud.
   - "Localisation suspecte": human validation required.
5. "Mes achats" shows the history and each order's agent pipeline.
6. Log out and log in as the admin (`/admin`). You see:
   - confirmed revenue, charts and the Financial Analyst analysis;
   - orders and fraud alerts (approve or reject);
   - users, courses, and agent activity.

## API (backend :4000, JSON `{status, data | errors}`)
| Route | Access |
|---|---|
| `GET /api/health` | public |
| `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` | public / user |
| `POST /api/auth/login/2fa` (second login step when 2FA is on: `{ challengeToken, code }`) | public |
| `POST /api/auth/2fa/setup`, `POST /api/auth/2fa/enable`, `POST /api/auth/2fa/disable` (TOTP, "Sécurité" tab) | user |
| `GET /api/courses`, `GET /api/courses/:id` | public |
| `GET/POST /api/conversations`, `GET/POST /api/conversations/:id/messages` | user (own data only) |
| `POST /api/purchases`, `GET /api/purchases`, `GET /api/purchases/:id` | user |
| `GET /api/admin/stats`, `insights`, `users`, `PATCH users/:id/role`, `courses`, `PATCH courses/:id`, `orders`, `orders/:id`, `alerts`, `POST alerts/:id/decision`, `agent-activity` | admin (role read from the DB) |

The backend calls the AI service (`/agents/sales`, `/workflow/purchase`, `/agents/financial`) server-side, with `X-API-Key` when `INTERNAL_API_KEY` is set.

## Rate limiting (backend)
Per client IP unless stated. A blocked request gets `429` with `Retry-After` and `RateLimit` headers; the frontend shows "Trop de tentatives. Réessayez dans N minutes."

| What | Limit |
|---|---|
| Whole API | 600 requests / 15 min |
| Failed logins | 10 / 15 min (successful logins do not count) |
| Failed logins on one account (any IP) | 10 / 15 min |
| Wrong 2FA codes | 10 / 15 min (plus 5 per login challenge) |
| Accounts created | 5 / hour |
| 2FA setup / enable / disable | 10 / 15 min |

Counters live in memory: they reset when the backend restarts (use a shared store such as Redis with several instances). The client IP comes from `X-Forwarded-For` only when the proxy is trusted (`TRUST_PROXY`, default `loopback` for the Vite dev proxy; `1` behind one hosting proxy). Values are in `backend/src/middlewares/rateLimit.js`.
