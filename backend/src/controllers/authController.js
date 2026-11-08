import { randomUUID } from "node:crypto";

import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DB_UNAVAILABLE_CODES = new Set(["ECONNREFUSED", "ENOTFOUND", "ETIMEDOUT", "ECONNRESET", "57P01", "57P03"]);

const fail = (res, status, ...errors) => res.status(status).json({ status: "error", errors });

const publicUser = (row) => ({
  id: row.id,
  name: row.name,
  email: row.email,
  role: row.role,
  createdAt: row.created_at,
});

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
        "SELECT id, name, email, role, password_hash FROM users WHERE email = $1",
        [email.trim().toLowerCase()],
      );
      const user = rows[0];
      const valid = await bcrypt.compare(password, user ? user.password_hash : dummyHash);
      if (!user || !valid) return fail(res, 401, "Invalid email or password");

      const accessToken = jwt.sign({ sub: String(user.id), role: user.role, email: user.email }, jwtSecret, {
        algorithm: "HS256",
        expiresIn: jwtExpiresIn,
      });
      return res.status(200).json({
        status: "ok",
        data: { accessToken, tokenType: "Bearer", expiresIn: jwtExpiresIn },
      });
    } catch (err) {
      return handleDbError(res, err, "Login");
    }
  };

  const me = async (req, res) => {
    if (!pool) return fail(res, 503, "Database is not configured");
    try {
      // Identity comes only from the verified JWT (set by the auth middleware), never from the client.
      const { rows } = await pool.query("SELECT id, name, email, role, created_at FROM users WHERE id = $1", [
        req.auth.userId,
      ]);
      if (!rows.length) return fail(res, 401, "User no longer exists");
      const user = publicUser(rows[0]);
      return res.status(200).json({ status: "ok", data: { userId: user.id, ...user } });
    } catch (err) {
      return handleDbError(res, err, "Fetching user");
    }
  };

  return { register, login, me };
}
