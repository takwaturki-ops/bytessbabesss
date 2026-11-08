import pg from "pg";

const { Pool } = pg;

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

/**
 * SSL options for a connection string.
 * - Local PostgreSQL (localhost, 127.0.0.1, ::1) usually runs without SSL: SSL is off
 *   unless the URL asks for it (sslmode=require / verify-ca / verify-full).
 * - sslmode=disable always turns it off.
 * - Any other host (Neon...) keeps the original setting.
 */
export function sslFor(connectionString) {
  let url;
  try {
    url = new URL(connectionString);
  } catch {
    return { rejectUnauthorized: false };
  }
  const sslmode = url.searchParams.get("sslmode");
  if (sslmode === "disable") {
    return false;
  }
  if (LOCAL_HOSTS.has(url.hostname) && !["require", "verify-ca", "verify-full"].includes(sslmode)) {
    return false;
  }
  // Kept from the original Neon setup. See README: certificate verification should be reviewed by the team.
  return { rejectUnauthorized: false };
}

/**
 * Create the single PostgreSQL pool used by the whole backend (Neon or local PostgreSQL).
 * Returns null when DATABASE_URL is not configured (the server still starts; DB routes answer 503).
 */
export function createPool(connectionString) {
  if (!connectionString) {
    return null;
  }
  const pool = new Pool({
    connectionString,
    ssl: sslFor(connectionString),
    connectionTimeoutMillis: 5000,
  });
  // An idle client losing its connection must not crash the process.
  pool.on("error", (err) => {
    console.error("PostgreSQL pool error:", err.message);
  });
  return pool;
}

/** "connected" | "unavailable" | "not_configured" - never throws. */
export async function checkDatabaseConnection(pool) {
  if (!pool) {
    return "not_configured";
  }
  try {
    await pool.query("SELECT 1");
    return "connected";
  } catch {
    return "unavailable";
  }
}
