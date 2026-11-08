import express from "express";

import { createAuthController } from "../controllers/authController.js";
import { createAuthMiddleware } from "../middlewares/authMiddleware.js";
import { createRateLimiters } from "../middlewares/rateLimit.js";

// Express 4 does not catch rejected promises: forward them to the error handler.
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

export function createAuthRouter({ rateLimits, limiters = createRateLimiters(rateLimits), ...options }) {
  const controller = createAuthController(options);
  const protect = createAuthMiddleware(options);
  const router = express.Router();

  router.post("/register", limiters.register, asyncHandler(controller.register));
  router.post("/login", limiters.login, limiters.loginAccount, asyncHandler(controller.login));
  router.get("/me", protect, asyncHandler(controller.me));

  // Two-factor authentication (TOTP)
  router.post("/login/2fa", limiters.twoFactor, asyncHandler(controller.loginTwoFactor));
  router.post("/2fa/setup", limiters.twoFactorSettings, protect, asyncHandler(controller.setupTwoFactor));
  router.post("/2fa/enable", limiters.twoFactorSettings, protect, asyncHandler(controller.enableTwoFactor));
  router.post("/2fa/disable", limiters.twoFactorSettings, protect, asyncHandler(controller.disableTwoFactor));

  return router;
}
