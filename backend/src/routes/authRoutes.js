import express from "express";

import { createAuthController } from "../controllers/authController.js";
import { createAuthMiddleware } from "../middlewares/authMiddleware.js";

// Express 4 does not catch rejected promises: forward them to the error handler.
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

export function createAuthRouter(options) {
  const controller = createAuthController(options);
  const protect = createAuthMiddleware(options);
  const router = express.Router();

  router.post("/register", asyncHandler(controller.register));
  router.post("/login", asyncHandler(controller.login));
  router.get("/me", protect, asyncHandler(controller.me));

  // Two-factor authentication (TOTP)
  router.post("/login/2fa", asyncHandler(controller.loginTwoFactor));
  router.post("/2fa/setup", protect, asyncHandler(controller.setupTwoFactor));
  router.post("/2fa/enable", protect, asyncHandler(controller.enableTwoFactor));
  router.post("/2fa/disable", protect, asyncHandler(controller.disableTwoFactor));

  return router;
}
