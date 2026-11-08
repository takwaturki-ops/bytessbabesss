import cors from "cors";
import express from "express";
import helmet from "helmet";

import { checkDatabaseConnection } from "./config/database.js";
import { createAuthRouter } from "./routes/authRoutes.js";

/**
 * Build the single Express application (without listening), so it can be started by src/server.js
 * or tested in-process.
 */
export function createApp({ pool, jwtSecret, jwtExpiresIn = "15m", corsOrigins = [], bcryptRounds = 12 }) {
  const app = express();

  // Middlewares (kept from the original server: helmet + cors + JSON body)
  app.use(helmet());
  app.use(cors({ origin: corsOrigins.length ? corsOrigins : false }));
  app.use(express.json({ limit: "100kb" }));

  // Health check: always 200 while the process runs; reports the database state separately.
  app.get("/api/health", async (req, res) => {
    res.status(200).json({
      status: "success",
      message: "FinTech Backend is running!",
      database: await checkDatabaseConnection(pool),
    });
  });

  app.use("/api/auth", createAuthRouter({ pool, jwtSecret, jwtExpiresIn, bcryptRounds }));

  app.use((req, res) => {
    res.status(404).json({ status: "error", errors: ["Route not found"] });
  });

  // Last-resort error handler: structured JSON, no stack traces or internal messages leaked.
  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    if (err.type === "entity.parse.failed") {
      return res.status(400).json({ status: "error", errors: ["Malformed JSON body"] });
    }
    if (err.type === "entity.too.large") {
      return res.status(413).json({ status: "error", errors: ["Request body too large"] });
    }
    console.error("Unhandled error:", err.message);
    return res.status(500).json({ status: "error", errors: ["Internal server error"] });
  });

  return app;
}
