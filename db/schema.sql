-- 9antra / SmartFin AI - PostgreSQL schema (Neon)
-- Additive and safe to re-run: never drops or modifies existing tables or data.
-- Apply with:  cd backend && npm run db:migrate   (also loads db/seed.sql)

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL       PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(254) NOT NULL UNIQUE,      -- stored lower-case by the backend
    password_hash VARCHAR(255) NOT NULL,             -- bcrypt hash, never the plain password
    role          VARCHAR(20)  NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Two-factor authentication (TOTP, authenticator apps). Added with ALTER so existing databases get the columns.
--   totp_secret    : base32 secret, set at enrolment (pending until totp_enabled is true). Never sent back after enrolment.
--   totp_enabled   : login asks for a 6-digit code only when TRUE.
--   totp_last_step : last 30-second time step accepted, so the same code can never be used twice (replay).
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret    VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled   BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_last_step BIGINT;

-- Course catalog. IDs and prices are the SAME as the AI service catalog (ai-services/data_generation/catalog.py):
-- the purchase workflow takes the price from that catalog, so prices are not editable from the admin UI.
CREATE TABLE IF NOT EXISTS courses (
    id             VARCHAR(20)   PRIMARY KEY,
    title          VARCHAR(200)  NOT NULL,
    title_ar       VARCHAR(200),
    category       VARCHAR(50)   NOT NULL,
    level          VARCHAR(20)   NOT NULL,
    price_tnd      NUMERIC(10,2) NOT NULL CHECK (price_tnd > 0),
    duration_hours INTEGER       NOT NULL,
    duration_weeks INTEGER       NOT NULL,
    description    TEXT          NOT NULL,
    is_active      BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id         SERIAL       PRIMARY KEY,
    user_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(200) NOT NULL DEFAULT 'Nouvelle conversation',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL      PRIMARY KEY,
    conversation_id INTEGER     NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT        NOT NULL,
    metadata        JSONB,                            -- sales agent result (intent, recommended courses...)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One row per purchase workflow run (SIMULATED payments). id = order_id returned by the AI workflow.
CREATE TABLE IF NOT EXISTS orders (
    id               VARCHAR(40)   PRIMARY KEY,
    user_id          INTEGER       NOT NULL REFERENCES users(id),
    course_id        VARCHAR(20)   NOT NULL REFERENCES courses(id),
    conversation_id  INTEGER       REFERENCES conversations(id) ON DELETE SET NULL,
    workflow_id      VARCHAR(40)   NOT NULL UNIQUE,
    amount_tnd       NUMERIC(10,2) NOT NULL,
    list_price_tnd   NUMERIC(10,2) NOT NULL,
    payment_method   VARCHAR(20)   NOT NULL,
    payment_scenario VARCHAR(30)   NOT NULL,
    status           VARCHAR(40)   NOT NULL,          -- paid | failed | pending | requires_review | awaiting_approval | blocked | approved_awaiting_payment | rejected
    final_status     VARCHAR(40)   NOT NULL,          -- final_status from POST /workflow/purchase
    next_step        VARCHAR(80),
    workflow_result  JSONB,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Only created when the Payment Agent actually processed the (simulated) payment event.
CREATE TABLE IF NOT EXISTS transactions (
    id                VARCHAR(50)   PRIMARY KEY,
    order_id          VARCHAR(40)   NOT NULL REFERENCES orders(id),
    user_id           INTEGER       NOT NULL REFERENCES users(id),
    amount_tnd        NUMERIC(10,2) NOT NULL,
    status            VARCHAR(20)   NOT NULL CHECK (status IN ('success', 'failed', 'pending', 'requires_review')),
    payment_confirmed BOOLEAN       NOT NULL DEFAULT FALSE,
    failure_reason    VARCHAR(100),
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    id          SERIAL      PRIMARY KEY,
    order_id    VARCHAR(40) NOT NULL REFERENCES orders(id),
    user_id     INTEGER     NOT NULL REFERENCES users(id),
    action      VARCHAR(30) NOT NULL,                 -- block | require_human_approval (deterministic fraud rules)
    risk_score  INTEGER     NOT NULL,
    flags       TEXT        NOT NULL DEFAULT '',
    explanation TEXT,
    status      VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'approved', 'rejected')),
    reviewed_by INTEGER     REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Execution trace of the five-agent workflow, one row per step.
CREATE TABLE IF NOT EXISTS agent_events (
    id          SERIAL      PRIMARY KEY,
    order_id    VARCHAR(40) REFERENCES orders(id),
    step        INTEGER     NOT NULL,
    name        VARCHAR(60) NOT NULL,
    agent       VARCHAR(60),
    status      VARCHAR(20) NOT NULL,
    decision    VARCHAR(60),
    summary     TEXT,
    mode        VARCHAR(20),
    duration_ms INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
