import cors from "cors";
import express from "express";
import helmet from "helmet";

import { checkDatabaseConnection } from "./config/database.js";
import { createAuthMiddleware, createRequireAdmin } from "./middlewares/authMiddleware.js";
import { createAdminRouter } from "./routes/adminRoutes.js";
import { createAuthRouter } from "./routes/authRoutes.js";
import { createConversationRouter } from "./routes/conversationRoutes.js";
import { createCourseRouter } from "./routes/courseRoutes.js";
import { createPurchaseRouter } from "./routes/purchaseRoutes.js";
import { createAiClient } from "./services/aiClient.js";
import { isDbUnavailable } from "./utils/http.js";

/**
 * Build the single Express application (without listening), so it can be started by src/server.js
 * or tested in-process.
 */
export function createApp({
  pool, jwtSecret, jwtExpiresIn = "15m", corsOrigins = [], bcryptRounds = 12,
  ai = createAiClient(), databaseMode = "postgres",
}) {
  const app = express();

  // Middlewares (kept from the original server: helmet + cors + JSON body)
  app.use(helmet());
  app.use(cors({ origin: corsOrigins.length ? corsOrigins : false }));
  app.use(express.json({ limit: "100kb" }));

  // Health check: always 200 while the process runs; reports database and AI service state separately.
  app.get("/api/health", async (req, res) => {
    let aiService = "down";
    try {
      const r = await ai.health();
      aiService = r.status === 200 ? `up (${r.body?.mode ?? "unknown"} mode)` : "down";
    } catch { /* reported as down */ }
    res.status(200).json({
      status: "success",
      message: "FinTech Backend is running!",
      database: await checkDatabaseConnection(pool),
      database_mode: pool ? databaseMode : null,
      ai_service: aiService,
    });
  });

  app.use("/api/auth", createAuthRouter({ pool, jwtSecret, jwtExpiresIn, bcryptRounds }));

  // Everything below needs a database and an authenticated user.
  const protect = createAuthMiddleware({ jwtSecret });
  const requireDb = (req, res, next) => (pool ? next() : res.status(503).json({ status: "error", errors: ["Database is not configured"] }));
  app.use("/api/courses", requireDb, createCourseRouter({ pool }));
  app.use("/api/conversations", requireDb, protect, createConversationRouter({ pool, ai }));
  app.use("/api/purchases", requireDb, protect, createPurchaseRouter({ pool, ai }));
  app.use("/api/admin", requireDb, protect, createRequireAdmin({ pool }), createAdminRouter({ pool, ai }));

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
    if (isDbUnavailable(err)) {
      return res.status(503).json({ status: "error", errors: ["Database unavailable, please try again later"] });
    }
    console.error("Unhandled error:", err.message);
    return res.status(500).json({ status: "error", errors: ["Internal server error"] });
  });

  return app;
}
