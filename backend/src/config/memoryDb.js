// LOCAL DEMO ONLY: in-memory PostgreSQL (pg-mem, a devDependency) loaded with db/schema.sql + db/seed.sql.
// Used when USE_IN_MEMORY_DB=true and no Neon database is available. Everything is lost when the server stops.
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import bcrypt from "bcrypt";

const dbDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..", "db");

export async function createMemoryPool({ demoAdmin } = {}) {
  const { newDb } = await import("pg-mem");
  const db = newDb();
  db.public.none(await readFile(path.join(dbDir, "schema.sql"), "utf8"));
  db.public.none(await readFile(path.join(dbDir, "seed.sql"), "utf8"));
  const { Pool } = db.adapters.createPg();
  const pool = new Pool();
  if (demoAdmin) {
    await pool.query(
      "INSERT INTO users (name, email, password_hash, role) VALUES ($1, $2, $3, 'admin')",
      [demoAdmin.name, demoAdmin.email.trim().toLowerCase(), await bcrypt.hash(demoAdmin.password, 12)],
    );
  }
  return pool;
}
