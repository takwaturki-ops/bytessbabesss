// Create (or promote) an admin account. Public registration can never create admins.
// Usage:  npm run create-admin -- <email> <password> [name]
import bcrypt from "bcrypt";

import { createPool } from "../src/config/database.js";
import { loadEnv } from "../src/config/env.js";

const [email, password, name = "Admin 9antra"] = process.argv.slice(2);
if (!email || !password || password.length < 8) {
  console.error("Usage: npm run create-admin -- <email> <password (8+ chars)> [name]");
  process.exit(1);
}

loadEnv();
const pool = createPool(process.env.DATABASE_URL);
if (!pool) {
  console.error("DATABASE_URL is not set. Nothing was changed.");
  process.exit(1);
}

try {
  const normalized = email.trim().toLowerCase();
  const existing = await pool.query("SELECT id FROM users WHERE email = $1", [normalized]);
  if (existing.rows.length) {
    await pool.query("UPDATE users SET role = 'admin' WHERE id = $1", [existing.rows[0].id]);
    console.log(`Existing user ${normalized} promoted to admin (password unchanged).`);
  } else {
    await pool.query("INSERT INTO users (name, email, password_hash, role) VALUES ($1, $2, $3, 'admin')",
      [name, normalized, await bcrypt.hash(password, 12)]);
    console.log(`Admin ${normalized} created.`);
  }
} catch (err) {
  console.error(`Failed: ${err.message}`);
  process.exitCode = 1;
} finally {
  await pool.end();
}
