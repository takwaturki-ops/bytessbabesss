import { rateLimit } from "express-rate-limit";

/*
 * Rate limiting (brute force and abuse protection).
 * Counters are kept in memory: they reset when the server restarts and are per process.
 * With several backend instances, use a shared store (Redis) instead.
 *
 * Clients are identified by IP (req.ip). Behind a proxy (the Vite dev server, nginx...) the real IP
 * comes from X-Forwarded-For, which Express only trusts from the proxies set in "trust proxy" (app.js).
 */

const MINUTE = 60 * 1000;

export const DEFAULT_RATE_LIMITS = {
  // Whole API, per IP: generous, only stops floods.
  api: { windowMs: 15 * MINUTE, limit: 600 },
  // Failed logins per IP (successful logins are not counted).
  login: { windowMs: 15 * MINUTE, limit: 10 },
  // Failed logins per account (stops one account being attacked from many IPs).
  loginAccount: { windowMs: 15 * MINUTE, limit: 10 },
  // Wrong 2FA codes per IP (on top of the 5 attempts per login challenge).
  twoFactor: { windowMs: 15 * MINUTE, limit: 10 },
  // Accounts created per IP.
  register: { windowMs: 60 * MINUTE, limit: 5 },
  // 2FA setup / enable / disable per IP.
  twoFactorSettings: { windowMs: 15 * MINUTE, limit: 10 },
};

function minutesLeft(req, windowMs) {
  const reset = req.rateLimit?.resetTime;
  const ms = reset instanceof Date ? reset.getTime() - Date.now() : windowMs;
  return Math.max(1, Math.ceil(ms / MINUTE));
}

function limiter({ windowMs, limit }, { message, ...options } = {}) {
  return rateLimit({
    windowMs,
    limit,
    standardHeaders: "draft-7", // RateLimit and RateLimit-Policy headers
    legacyHeaders: false,
    // Same JSON format as every other error, plus Retry-After (set by the library).
    handler: (req, res) => {
      res.status(429).json({
        status: "error",
        errors: [`${message} Try again in ${minutesLeft(req, windowMs)} minute(s).`],
      });
    },
    ...options,
  });
}

/** Build all limiters. Pass `false` to disable rate limiting (unit tests only). */
export function createRateLimiters(config = {}) {
  if (config === false) {
    const pass = (req, res, next) => next();
    return { api: pass, login: pass, loginAccount: pass, twoFactor: pass, register: pass, twoFactorSettings: pass };
  }
  const c = { ...DEFAULT_RATE_LIMITS, ...config };
  return {
    api: limiter(c.api, { message: "Too many requests." }),
    login: limiter(c.login, { message: "Too many failed login attempts.", skipSuccessfulRequests: true }),
    loginAccount: limiter(c.loginAccount, {
      message: "Too many failed login attempts for this account.",
      skipSuccessfulRequests: true,
      // Keyed by email, so requests without one are left to the per-IP limiter.
      skip: (req) => typeof req.body?.email !== "string" || !req.body.email.trim(),
      keyGenerator: (req) => `account:${req.body.email.trim().toLowerCase()}`,
    }),
    twoFactor: limiter(c.twoFactor, { message: "Too many wrong codes.", skipSuccessfulRequests: true }),
    // Only accounts actually created count (a form with a typo is not abuse).
    register: limiter(c.register, { message: "Too many accounts created from this network.", skipFailedRequests: true }),
    twoFactorSettings: limiter(c.twoFactorSettings, { message: "Too many two-factor requests." }),
  };
}
