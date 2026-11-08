import pg from "pg";

const { Pool } = pg;

/**
 * Create the single Neon PostgreSQL pool used by the whole backend.
 * Returns null when DATABASE_URL is not configured (the server still starts; DB routes answer 503).
 */
export function createPool(connectionString) {
  if (!connectionString) {
    return null;
  }
  const pool = new Pool({
    connectionString,
    // Kept from the original Neon setup. See README: certificate verification should be reviewed by the team.
    ssl: { rejectUnauthorized: false },
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
