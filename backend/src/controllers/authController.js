import { randomUUID } from "node:crypto";

import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";

import { enrolmentData, generateSecret, verifyCode } from "../services/2faService.js";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DB_UNAVAILABLE_CODES = new Set(["ECONNREFUSED", "ENOTFOUND", "ETIMEDOUT", "ECONNRESET", "57P01", "57P03"]);

const fail = (res, status, ...errors) => res.status(status).json({ status: "error", errors });

const publicUser = (row) => ({
  id: row.id,
  name: row.name,
  email: row.email,
  role: row.role,
  createdAt: row.created_at,
  twoFactorEnabled: Boolean(row.totp_enabled),
});

// Second login step (2FA): short-lived token that only proves the password was correct.
// Its audience makes it unusable as an access token (the auth middleware refuses any token with an audience).
export const TWO_FACTOR_AUDIENCE = "9antra-2fa-challenge";
const CHALLENGE_TTL = "5m";
const MAX_CODE_ATTEMPTS = 5;

function isDbUnavailable(err) {
  return (
    DB_UNAVAILABLE_CODES.has(err?.code) ||
    (typeof err?.code === "string" && err.code.startsWith("08")) ||
    /timeout|terminated|connect/i.test(err?.message || "")
  );
}

function handleDbError(res, err, action) {
  if (isDbUnavailable(err)) {
    return fail(res, 503, "Database unavailable, please try again later");
  }
  console.error(`${action} failed:`, err?.message);
  return fail(res, 500, `${action} failed`);
}

export function createAuthController({ pool, jwtSecret, jwtExpiresIn = "15m", bcryptRounds = 12 }) {
  if (!jwtSecret) {
    throw new Error("JWT_SECRET is required");
  }
  // Compared against when the email is unknown, so a login attempt costs the same time
  // whether or not the account exists (prevents discovering registered emails by timing).
  const dummyHash = bcrypt.hashSync(randomUUID(), bcryptRounds);
  // Wrong 2FA codes per challenge token (jti -> count). A challenge dies after MAX_CODE_ATTEMPTS or 5 minutes.
  const challengeAttempts = new Map();

  const issueAccessToken = (user) => {
    const accessToken = jwt.sign({ sub: String(user.id), role: user.role, email: user.email }, jwtSecret, {
      algorithm: "HS256",
      expiresIn: jwtExpiresIn,
    });
    return { accessToken, tokenType: "Bearer", expiresIn: jwtExpiresIn };
  };

  const register = async (req, res) => {
    const { name, email, password } = req.body || {};
    const errors = [];
    const cleanName = typeof name === "string" ? name.trim() : "";
    const cleanEmail = typeof email === "string" ? email.trim().toLowerCase() : "";

    if (!cleanName || !cleanEmail || typeof password !== "string" || !password) {
      errors.push("Name, email and password are required");
    } else {
      if (cleanName.length < 2 || cleanName.length > 100) errors.push("Name must be 2 to 100 characters");
      if (cleanEmail.length > 254 || !EMAIL_RE.test(cleanEmail)) errors.push("Email format is invalid");
      if (password.length < 8) errors.push("Password must be at least 8 characters");
      if (Buffer.byteLength(password, "utf8") > 72) errors.push("Password must be at most 72 bytes");
    }
    if (errors.length) return fail(res, 422, ...errors);
    if (!pool) return fail(res, 503, "Database is not configured");

    try {
      const existing = await pool.query("SELECT id FROM users WHERE email = $1", [cleanEmail]);
      if (existing.rows.length) return fail(res, 409, "Email is already registered");

      const passwordHash = await bcrypt.hash(password, bcryptRounds);
      // role is never taken from the request: new accounts are always customers.
      const { rows } = await pool.query(
        "INSERT INTO users (name, email, password_hash) VALUES ($1, $2, $3) " +
          "RETURNING id, name, email, role, created_at",
        [cleanName, cleanEmail, passwordHash],
      );
      const user = publicUser(rows[0]);
      return res.status(201).json({ status: "ok", data: { userId: user.id, email: user.email, user } });
    } catch (err) {
      if (err?.code === "23505") return fail(res, 409, "Email is already registered"); // concurrent duplicate
      return handleDbError(res, err, "Registration");
    }
  };

  const login = async (req, res) => {
    const { email, password } = req.body || {};
    if (typeof email !== "string" || !email.trim() || typeof password !== "string" || !password) {
      return fail(res, 422, "Email and password are required");
    }
    if (!pool) return fail(res, 503, "Database is not configured");

    try {
      const { rows } = await pool.query(
        "SELECT id, name, email, role, password_hash, totp_enabled FROM users WHERE email = $1",
        [email.trim().toLowerCase()],
      );
      const user = rows[0];
      const valid = await bcrypt.compare(password, user ? user.password_hash : dummyHash);
      if (!user || !valid) return fail(res, 401, "Invalid email or password");

      if (user.totp_enabled) {
        // Password is correct but 2FA is on: no access token yet, the client must send a 6-digit code.
        const jti = randomUUID();
        challengeAttempts.set(jti, 0);
        setTimeout(() => challengeAttempts.delete(jti), 5 * 60 * 1000).unref();
        const challengeToken = jwt.sign({ sub: String(user.id) }, jwtSecret, {
          algorithm: "HS256",
          audience: TWO_FACTOR_AUDIENCE,
          expiresIn: CHALLENGE_TTL,
          jwtid: jti,
        });
        return res.status(200).json({ status: "ok", data: { twoFactorRequired: true, challengeToken } });
      }

      return res.status(200).json({ status: "ok", data: issueAccessToken(user) });
    } catch (err) {
      return handleDbError(res, err, "Login");
    }
  };

  const me = async (req, res) => {
    if (!pool) return fail(res, 503, "Database is not configured");
    try {
      // Identity comes only from the verified JWT (set by the auth middleware), never from the client.
      const { rows } = await pool.query("SELECT id, name, email, role, created_at, totp_enabled FROM users WHERE id = $1", [
        req.auth.userId,
      ]);
      if (!rows.length) return fail(res, 401, "User no longer exists");
      const user = publicUser(rows[0]);
      return res.status(200).json({ status: "ok", data: { userId: user.id, ...user } });
    } catch (err) {
      return handleDbError(res, err, "Fetching user");
    }
  };

  // POST /api/auth/login/2fa  { challengeToken, code } -> access token
  const loginTwoFactor = async (req, res) => {
    const { challengeToken, code } = req.body || {};
    if (typeof challengeToken !== "string" || typeof code !== "string") {
      return fail(res, 422, "challengeToken and code are required");
    }
    let payload;
    try {
      payload = jwt.verify(challengeToken, jwtSecret, { algorithms: ["HS256"], audience: TWO_FACTOR_AUDIENCE });
    } catch {
      return fail(res, 401, "Login session expired, please sign in again");
    }
    const attempts = challengeAttempts.get(payload.jti);
    if (attempts === undefined || attempts >= MAX_CODE_ATTEMPTS) {
      challengeAttempts.delete(payload.jti);
      return fail(res, 401, "Too many attempts, please sign in again");
    }
    if (!pool) return fail(res, 503, "Database is not configured");

    try {
      const { rows } = await pool.query(
        "SELECT id, email, role, totp_secret, totp_enabled, totp_last_step FROM users WHERE id = $1",
        [Number(payload.sub)],
      );
      const user = rows[0];
      if (!user || !user.totp_enabled) return fail(res, 401, "Login session expired, please sign in again");

      const step = verifyCode(code, user.totp_secret, { lastStep: user.totp_last_step });
      // Atomic: two requests with the same code cannot both succeed.
      const accepted = step !== null && (await pool.query(
        "UPDATE users SET totp_last_step = $2 WHERE id = $1 AND (totp_last_step IS NULL OR totp_last_step < $2)",
        [user.id, step],
      )).rowCount === 1;
      if (!accepted) {
        challengeAttempts.set(payload.jti, attempts + 1);
        return fail(res, 401, "Invalid code");
      }
      challengeAttempts.delete(payload.jti);
      return res.status(200).json({ status: "ok", data: issueAccessToken(user) });
    } catch (err) {
      return handleDbError(res, err, "Login");
    }
  };

  // POST /api/auth/2fa/setup (logged in) -> new pending secret + QR code. 2FA stays OFF until /2fa/enable.
  const setupTwoFactor = async (req, res) => {
    if (!pool) return fail(res, 503, "Database is not configured");
    try {
      const { rows } = await pool.query("SELECT email, totp_enabled FROM users WHERE id = $1", [req.auth.userId]);
      if (!rows.length) return fail(res, 401, "User no longer exists");
      if (rows[0].totp_enabled) return fail(res, 409, "Two-factor authentication is already enabled");

      const secret = generateSecret();
      await pool.query("UPDATE users SET totp_secret = $2, totp_last_step = NULL WHERE id = $1", [req.auth.userId, secret]);
      const { otpauthUrl, qrCodeDataUrl } = await enrolmentData(secret, rows[0].email);
      // The secret is shown only now (manual entry in the app); it is never returned again.
      return res.status(200).json({ status: "ok", data: { secret, otpauthUrl, qrCodeDataUrl } });
    } catch (err) {
      return handleDbError(res, err, "Two-factor setup");
    }
  };

  // POST /api/auth/2fa/enable { code } (logged in) -> turns 2FA on once the app produces a valid code.
  const enableTwoFactor = async (req, res) => {
    const { code } = req.body || {};
    if (typeof code !== "string") return fail(res, 422, "code is required");
    if (!pool) return fail(res, 503, "Database is not configured");
    try {
      const { rows } = await pool.query("SELECT totp_secret, totp_enabled FROM users WHERE id = $1", [req.auth.userId]);
      if (!rows.length) return fail(res, 401, "User no longer exists");
      if (rows[0].totp_enabled) return fail(res, 409, "Two-factor authentication is already enabled");
      if (!rows[0].totp_secret) return fail(res, 400, "Start the setup first");

      const step = verifyCode(code, rows[0].totp_secret);
      if (step === null) return fail(res, 400, "Invalid code");
      await pool.query("UPDATE users SET totp_enabled = TRUE, totp_last_step = $2 WHERE id = $1", [req.auth.userId, step]);
      return res.status(200).json({ status: "ok", data: { twoFactorEnabled: true } });
    } catch (err) {
      return handleDbError(res, err, "Enabling two-factor authentication");
    }
  };

  // POST /api/auth/2fa/disable { password, code } (logged in) -> both required, so a stolen token is not enough.
  const disableTwoFactor = async (req, res) => {
    const { password, code } = req.body || {};
    if (typeof password !== "string" || !password || typeof code !== "string") {
      return fail(res, 422, "password and code are required");
    }
    if (!pool) return fail(res, 503, "Database is not configured");
    try {
      const { rows } = await pool.query(
        "SELECT password_hash, totp_secret, totp_enabled, totp_last_step FROM users WHERE id = $1",
        [req.auth.userId],
      );
      if (!rows.length) return fail(res, 401, "User no longer exists");
      const user = rows[0];
      if (!user.totp_enabled) return fail(res, 400, "Two-factor authentication is not enabled");
      if (!(await bcrypt.compare(password, user.password_hash))) return fail(res, 401, "Invalid password");
      if (verifyCode(code, user.totp_secret, { lastStep: user.totp_last_step }) === null) {
        return fail(res, 400, "Invalid code");
      }
      await pool.query(
        "UPDATE users SET totp_enabled = FALSE, totp_secret = NULL, totp_last_step = NULL WHERE id = $1",
        [req.auth.userId],
      );
      return res.status(200).json({ status: "ok", data: { twoFactorEnabled: false } });
    } catch (err) {
      return handleDbError(res, err, "Disabling two-factor authentication");
    }
  };

  return { register, login, me, loginTwoFactor, setupTwoFactor, enableTwoFactor, disableTwoFactor };
}
