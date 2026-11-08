// Apply db/schema.sql to the configured database (additive: CREATE TABLE IF NOT EXISTS only).
// Usage:  npm run db:migrate
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createPool } from "../src/config/database.js";
import { loadEnv } from "../src/config/env.js";

const schemaPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "db", "schema.sql");
const REQUIRED_COLUMNS = "id, name, email, password_hash, role, created_at";

loadEnv();
const pool = createPool(process.env.DATABASE_URL);
if (!pool) {
  console.error("DATABASE_URL is not set (backend/.env or <repo>/.env.local). Nothing was changed.");
  process.exit(1);
}

try {
  const sql = await readFile(schemaPath, "utf8");
  await pool.query(sql);
  // If a "users" table already existed with another structure, CREATE TABLE IF NOT EXISTS skipped it:
  // verify the columns the backend needs instead of failing later at login.
  await pool.query(`SELECT ${REQUIRED_COLUMNS} FROM users LIMIT 0`);
  console.log(`Schema applied from ${schemaPath}; users table has the required columns.`);
} catch (err) {
  console.error(`Migration failed: ${err.message}`);
  console.error(`If a users table already exists, it must provide: ${REQUIRED_COLUMNS}. No table was dropped.`);
  process.exitCode = 1;
} finally {
  await pool.end();
}
