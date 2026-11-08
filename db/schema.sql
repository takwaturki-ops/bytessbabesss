-- 9antra / SmartFin AI - PostgreSQL schema (Neon)
-- Additive and safe to re-run: never drops or modifies existing tables or data.
-- Apply with:  cd backend && npm run db:migrate

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL       PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(254) NOT NULL UNIQUE,      -- stored lower-case by the backend
    password_hash VARCHAR(255) NOT NULL,             -- bcrypt hash, never the plain password
    role          VARCHAR(20)  NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
