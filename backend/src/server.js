import { createApp } from "./app.js";
import { checkDatabaseConnection, createPool } from "./config/database.js";
import { getConfig, loadEnv } from "./config/env.js";
import { createAiClient } from "./services/aiClient.js";

// Single startup entry point of the backend:  npm start  ->  node src/server.js
loadEnv();

let config;
try {
  config = getConfig();
} catch (err) {
  console.error(`Configuration error: ${err.message}`);
  process.exit(1);
}
if (config.weakSecret) {
  console.warn("Warning: JWT_SECRET is shorter than 32 characters; use a long random value.");
}

let pool;
let databaseMode = "postgres";
if (config.inMemoryDb) {
  const { createMemoryPool } = await import("./config/memoryDb.js");
  pool = await createMemoryPool({ demoAdmin: config.demoAdmin });
  databaseMode = "in-memory (demo only, data lost on restart)";
  console.warn("USE_IN_MEMORY_DB=true: using an IN-MEMORY database (pg-mem). Not Neon. Data is lost on restart.");
  if (config.demoAdmin) console.warn(`Demo admin account created: ${config.demoAdmin.email}`);
} else {
  console.log("DATABASE_URL chargée :", Boolean(config.databaseUrl));
  pool = createPool(config.databaseUrl);
}

const app = createApp({
  pool,
  jwtSecret: config.jwtSecret,
  jwtExpiresIn: config.jwtExpiresIn,
  corsOrigins: config.corsOrigins,
  ai: createAiClient({ baseUrl: config.aiServiceUrl, apiKey: config.internalApiKey, timeoutMs: config.aiTimeoutMs }),
  databaseMode,
});

const database = await checkDatabaseConnection(pool);
if (database === "connected") {
  // Only the host is logged, never the full connection string (it contains the password).
  const host = config.databaseUrl ? new URL(config.databaseUrl).hostname : "";
  console.log(config.inMemoryDb ? "In-memory database ready." : `Connexion réussie à PostgreSQL (${host}) !`);
} else {
  console.error(`PostgreSQL ${database}: the server starts, database routes will answer 503 until it is reachable.`);
}
console.log(`AI service: ${config.aiServiceUrl}`);

const server = app.listen(config.port, () => {
  console.log(`Server running on http://localhost:${config.port}`);
});

const shutdown = () => {
  server.close(() => {
    Promise.resolve(pool?.end?.()).finally(() => process.exit(0));
  });
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
