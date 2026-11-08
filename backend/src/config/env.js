import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const backendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

/**
 * Load environment files without overriding variables already set in the shell.
 * 1. backend/.env        (recommended location)
 * 2. <repo>/.env.local   (location already used by the original Neon setup)
 * Paths are resolved from this file, so the server works whatever the current directory is.
 */
export function loadEnv() {
  for (const file of [path.join(backendDir, ".env"), path.join(backendDir, "..", ".env.local")]) {
    dotenv.config({ path: file, quiet: true });
  }
}

/** Read and validate configuration. Throws when a required value is missing. */
export function getConfig(env = process.env) {
  const jwtSecret = env.JWT_SECRET;
  if (!jwtSecret || !jwtSecret.trim()) {
    throw new Error("JWT_SECRET is required (set it in backend/.env). No default secret is used.");
  }
  return {
    port: Number(env.PORT) || 4000,
    databaseUrl: env.DATABASE_URL || null,
    jwtSecret,
    jwtExpiresIn: env.JWT_EXPIRES_IN || "15m",
    corsOrigins: (env.CORS_ORIGINS || "http://localhost:5173")
      .split(",")
      .map((origin) => origin.trim())
      .filter(Boolean),
    weakSecret: jwtSecret.length < 32,
  };
}
