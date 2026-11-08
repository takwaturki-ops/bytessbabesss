import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const backendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

/**
 * Load environment files without overriding variables already set in the shell.
 * 1. backend/.env        (recommended location)
 * 2. <repo>/.env.local   (location already used by the original Neon setup)
 * Paths are resolved from this file, so the server works whatever the current directory is.
 */
export function loadEnv() {
  for (const file of [path.join(backendDir, ".env"), path.join(backendDir, "..", ".env.local")]) {
    dotenv.config({ path: file, quiet: true });
  }
}

function parseTrustProxy(value) {
  const v = (value ?? "").trim();
  if (!v) return "loopback";
  if (v === "false") return false;
  if (/^\d+$/.test(v)) return Number(v);
  return v;
}

/** Read and validate configuration. Throws when a required value is missing. */
export function getConfig(env = process.env) {
  const jwtSecret = env.JWT_SECRET;
  if (!jwtSecret || !jwtSecret.trim()) {
    throw new Error("JWT_SECRET is required (set it in backend/.env). No default secret is used.");
  }
  return {
    port: Number(env.PORT) || 4000,
    databaseUrl: env.DATABASE_URL || null,
    jwtSecret,
    jwtExpiresIn: env.JWT_EXPIRES_IN || "15m",
    corsOrigins: (env.CORS_ORIGINS || "http://localhost:5173")
      .split(",")
      .map((origin) => origin.trim())
      .filter(Boolean),
    weakSecret: jwtSecret.length < 32,
    // Express "trust proxy": who may set X-Forwarded-For (client IP for rate limiting).
    // Default "loopback" (Vite dev proxy on this machine). Behind one hosting proxy use 1; no proxy: false.
    trustProxy: parseTrustProxy(env.TRUST_PROXY),
    // AI service (ai-services/, FastAPI). INTERNAL_API_KEY is sent server-side as X-API-Key.
    aiServiceUrl: env.AI_SERVICE_URL || "http://localhost:8001",
    internalApiKey: env.INTERNAL_API_KEY || "",
    aiTimeoutMs: Number(env.AI_TIMEOUT_MS) || 20000,
    // LOCAL DEMO ONLY: in-memory PostgreSQL (pg-mem) when no Neon database is available. Data is lost on restart.
    inMemoryDb: env.USE_IN_MEMORY_DB === "true",
    demoAdmin: env.DEMO_ADMIN_EMAIL && env.DEMO_ADMIN_PASSWORD
      ? { email: env.DEMO_ADMIN_EMAIL, password: env.DEMO_ADMIN_PASSWORD, name: env.DEMO_ADMIN_NAME || "Admin 9antra" }
      : null,
  };
}
