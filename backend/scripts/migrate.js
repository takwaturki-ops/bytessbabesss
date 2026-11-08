// Apply db/schema.sql then db/seed.sql (additive: CREATE TABLE IF NOT EXISTS / INSERT ... ON CONFLICT DO NOTHING).
// Usage:  npm run db:migrate
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createPool } from "../src/config/database.js";
import { loadEnv } from "../src/config/env.js";

const dbDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "db");
// Columns the backend relies on; an older table with another structure is reported instead of failing later.
const REQUIRED = {
  users: "id, name, email, password_hash, role, created_at",
  courses: "id, title, category, level, price_tnd, duration_hours, duration_weeks, description, is_active",
  conversations: "id, user_id, title, created_at, updated_at",
  messages: "id, conversation_id, role, content, metadata, created_at",
  orders: "id, user_id, course_id, workflow_id, amount_tnd, status, final_status, workflow_result, created_at",
  transactions: "id, order_id, user_id, amount_tnd, status, payment_confirmed, created_at",
  fraud_alerts: "id, order_id, user_id, action, risk_score, flags, status, created_at",
  agent_events: "id, order_id, step, name, agent, status, decision, summary, created_at",
};

loadEnv();
const pool = createPool(process.env.DATABASE_URL);
if (!pool) {
  console.error("DATABASE_URL is not set (backend/.env or <repo>/.env.local). Nothing was changed.");
  process.exit(1);
}

try {
  for (const file of ["schema.sql", "seed.sql"]) {
    await pool.query(await readFile(path.join(dbDir, file), "utf8"));
    console.log(`Applied db/${file}`);
  }
  for (const [table, columns] of Object.entries(REQUIRED)) {
    await pool.query(`SELECT ${columns} FROM ${table} LIMIT 0`);
  }
  const { rows } = await pool.query("SELECT COUNT(*)::int AS n FROM courses");
  console.log(`All tables have the required columns. Courses in catalog: ${rows[0].n}.`);
} catch (err) {
  console.error(`Migration failed: ${err.message}`);
  console.error("No table was dropped. An existing table may lack columns listed in scripts/migrate.js.");
  process.exitCode = 1;
} finally {
  await pool.end();
}
