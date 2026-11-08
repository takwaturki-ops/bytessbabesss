import { createApp } from "./app.js";
import { checkDatabaseConnection, createPool } from "./config/database.js";
import { getConfig, loadEnv } from "./config/env.js";

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

console.log("DATABASE_URL chargée :", Boolean(config.databaseUrl));
const pool = createPool(config.databaseUrl);
const app = createApp({
  pool,
  jwtSecret: config.jwtSecret,
  jwtExpiresIn: config.jwtExpiresIn,
  corsOrigins: config.corsOrigins,
});

const database = await checkDatabaseConnection(pool);
if (database === "connected") {
  console.log("Connexion réussie à Neon PostgreSQL !");
} else {
  console.error(`PostgreSQL ${database}: the server starts, authentication routes will answer 503 until it is reachable.`);
}

const server = app.listen(config.port, () => {
  console.log(`Server running on http://localhost:${config.port}`);
});

const shutdown = () => {
  server.close(() => {
    Promise.resolve(pool?.end()).finally(() => process.exit(0));
  });
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
