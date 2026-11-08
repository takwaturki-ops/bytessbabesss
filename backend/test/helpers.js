// Test helpers: in-memory PostgreSQL (pg-mem) loaded with the real db/schema.sql, and an app on a random port.
import { once } from "node:events";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { newDb } from "pg-mem";

import { createApp } from "../src/app.js";

export const TEST_SECRET = "test-only-secret-0123456789-abcdefghijklmnopqrstuvwxyz";
export const SCHEMA_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "db", "schema.sql");

export function createMemoryPool() {
  const db = newDb();
  db.public.none(readFileSync(SCHEMA_PATH, "utf8"));
  db.public.none(readFileSync(SCHEMA_PATH.replace("schema.sql", "seed.sql"), "utf8"));
  const { Pool } = db.adapters.createPg();
  return new Pool();
}

export async function startApp({ pool = createMemoryPool(), ...overrides } = {}) {
  const app = createApp({
    pool,
    jwtSecret: TEST_SECRET,
    jwtExpiresIn: "15m",
    corsOrigins: ["http://localhost:5173"],
    bcryptRounds: 4, // fast hashing for tests only (production default is 12)
    ...overrides,
  });
  const server = app.listen(0, "127.0.0.1");
  await once(server, "listening");
  const base = `http://127.0.0.1:${server.address().port}`;

  async function request(method, urlPath, body, headers = {}) {
    const res = await fetch(base + urlPath, {
      method,
      headers: { "content-type": "application/json", ...headers },
      body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
    });
    const json = await res.json().catch(() => null);
    return { status: res.status, body: json, headers: res.headers };
  }

  return { base, pool, request, close: () => new Promise((resolve) => server.close(resolve)) };
}
