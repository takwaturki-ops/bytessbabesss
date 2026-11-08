// Authentication regression tests (in-memory PostgreSQL via pg-mem; no Neon credentials needed).
import assert from "node:assert/strict";
import { after, before, describe, test } from "node:test";

import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";

import { startApp, TEST_SECRET } from "./helpers.js";

const USER = { name: "Amine Ben Ali", email: "amine@example.com", password: "s3cure-passw0rd" };

describe("authentication API", () => {
  let ctx;
  before(async () => {
    ctx = await startApp();
  });
  after(async () => {
    await ctx.close();
  });

  const login = (email, password) => ctx.request("POST", "/api/auth/login", { email, password });
  const me = (token) => ctx.request("GET", "/api/auth/me", undefined, token ? { authorization: `Bearer ${token}` } : {});

  test("GET /api/health returns 200", async () => {
    const res = await ctx.request("GET", "/api/health");
    assert.equal(res.status, 200);
    assert.equal(res.body.status, "success");
    assert.equal(res.body.database, "connected");
  });

  test("registration creates a database user (201) without returning the hash", async () => {
    const res = await ctx.request("POST", "/api/auth/register", USER);
    assert.equal(res.status, 201);
    assert.equal(res.body.status, "ok");
    assert.equal(res.body.data.email, USER.email);
    assert.equal(res.body.data.user.role, "customer");
    assert.ok(Number.isInteger(res.body.data.userId));
    assert.ok(!JSON.stringify(res.body).includes("password"), "no password or hash in the response");

    const { rows } = await ctx.pool.query("SELECT name, email, role FROM users WHERE email = $1", [USER.email]);
    assert.deepEqual(rows[0], { name: USER.name, email: USER.email, role: "customer" });
  });

  test("password is stored as a bcrypt hash, never in plain text", async () => {
    const { rows } = await ctx.pool.query("SELECT password_hash FROM users WHERE email = $1", [USER.email]);
    const hash = rows[0].password_hash;
    assert.notEqual(hash, USER.password);
    assert.match(hash, /^\$2[aby]\$\d{2}\$/);
    assert.equal(await bcrypt.compare(USER.password, hash), true);
  });

  test("duplicate email is rejected with 409 (case-insensitive)", async () => {
    const res = await ctx.request("POST", "/api/auth/register", { ...USER, email: "AMINE@Example.com" });
    assert.equal(res.status, 409);
    assert.deepEqual(res.body, { status: "error", errors: ["Email is already registered"] });
    const { rows } = await ctx.pool.query("SELECT COUNT(*)::int AS n FROM users");
    assert.equal(rows[0].n, 1);
  });

  test("role cannot be chosen by the client at registration", async () => {
    const res = await ctx.request("POST", "/api/auth/register", {
      name: "Eve", email: "eve@example.com", password: "password-eve", role: "admin",
    });
    assert.equal(res.status, 201);
    assert.equal(res.body.data.user.role, "customer");
  });

  test("correct password permits login and returns a signed JWT", async () => {
    const res = await login("Amine@Example.com", USER.password);
    assert.equal(res.status, 200);
    assert.equal(res.body.data.tokenType, "Bearer");
    const payload = jwt.verify(res.body.data.accessToken, TEST_SECRET, { algorithms: ["HS256"] });
    assert.equal(payload.email, USER.email);
    assert.ok(payload.exp > payload.iat);
  });

  test("incorrect password returns 401", async () => {
    const res = await login(USER.email, "wrong-password");
    assert.equal(res.status, 401);
    assert.deepEqual(res.body, { status: "error", errors: ["Invalid email or password"] });
  });

  test("unknown email returns the same 401 message (no account enumeration)", async () => {
    const res = await login("nobody@example.com", USER.password);
    assert.equal(res.status, 401);
    assert.deepEqual(res.body.errors, ["Invalid email or password"]);
  });

  test("SQL injection attempts are treated as plain data", async () => {
    const res = await login("' OR '1'='1' --", "' OR '1'='1' --");
    assert.equal(res.status, 401);
    const reg = await ctx.request("POST", "/api/auth/register", { name: "x'); DROP TABLE users;--", email: "a'--@x", password: "password123" });
    assert.equal(reg.status, 422);
    const { rows } = await ctx.pool.query("SELECT COUNT(*)::int AS n FROM users");
    assert.ok(rows[0].n >= 1, "users table still exists");
  });

  test("missing token is rejected with 401", async () => {
    const res = await me();
    assert.equal(res.status, 401);
    assert.deepEqual(res.body.errors, ["Authentication required"]);
    const wrongScheme = await ctx.request("GET", "/api/auth/me", undefined, { authorization: "Basic abc" });
    assert.equal(wrongScheme.status, 401);
  });

  test("invalid tokens are rejected with 401 (garbage, other secret, tampered, alg none, expired)", async () => {
    const good = (await login(USER.email, USER.password)).body.data.accessToken;
    const otherSecret = jwt.sign({ sub: "1", role: "admin" }, "attacker-secret");
    const [h, , s] = good.split(".");
    const forgedBody = Buffer.from(JSON.stringify({ sub: "2", role: "admin" })).toString("base64url");
    const tampered = `${h}.${forgedBody}.${s}`;
    const algNone = `${Buffer.from('{"alg":"none","typ":"JWT"}').toString("base64url")}.${forgedBody}.`;
    for (const token of ["not-a-jwt", otherSecret, tampered, algNone]) {
      const res = await me(token);
      assert.equal(res.status, 401, `token should be rejected: ${token.slice(0, 20)}`);
      assert.deepEqual(res.body.errors, ["Invalid token"]);
    }
    const expired = jwt.sign({ sub: "1" }, TEST_SECRET, { algorithm: "HS256", expiresIn: -10 });
    const res = await me(expired);
    assert.equal(res.status, 401);
    assert.deepEqual(res.body.errors, ["Token expired"]);
  });

  test("/me returns the authenticated user's database record, ignoring client-supplied ids", async () => {
    const token = (await login(USER.email, USER.password)).body.data.accessToken;
    const res = await ctx.request("GET", "/api/auth/me?userId=2", undefined, {
      authorization: `Bearer ${token}`, "x-user-id": "2",
    });
    assert.equal(res.status, 200);
    const { rows } = await ctx.pool.query("SELECT id, name, email, role FROM users WHERE email = $1", [USER.email]);
    assert.equal(res.body.data.userId, rows[0].id);
    assert.equal(res.body.data.id, rows[0].id);
    assert.equal(res.body.data.name, USER.name);
    assert.equal(res.body.data.email, USER.email);
    assert.equal(res.body.data.role, "customer");
    assert.ok(res.body.data.createdAt);
    assert.ok(!("password_hash" in res.body.data) && !("passwordHash" in res.body.data));
  });

  test("/me with a valid token for a deleted user returns 401", async () => {
    const ghost = jwt.sign({ sub: "99999", role: "customer" }, TEST_SECRET, { algorithm: "HS256", expiresIn: "5m" });
    const res = await me(ghost);
    assert.equal(res.status, 401);
  });
});

describe("input validation", () => {
  let ctx;
  before(async () => {
    ctx = await startApp();
  });
  after(async () => {
    await ctx.close();
  });

  const cases = [
    [{}, "Name, email and password are required"],
    [{ name: "Ab", email: "ab@example.com" }, "Name, email and password are required"],
    [{ name: "Ab", email: "not-an-email", password: "password123" }, "Email format is invalid"],
    [{ name: "Ab", email: "ab@example.com", password: "short" }, "Password must be at least 8 characters"],
    [{ name: "A", email: "ab@example.com", password: "password123" }, "Name must be 2 to 100 characters"],
    [{ name: "Ab", email: "ab@example.com", password: "é".repeat(40) }, "Password must be at most 72 bytes"],
    [{ name: ["Ab"], email: "ab@example.com", password: "password123" }, "Name, email and password are required"],
  ];
  for (const [body, message] of cases) {
    test(`register 422: ${message} (${JSON.stringify(body).slice(0, 40)})`, async () => {
      const res = await ctx.request("POST", "/api/auth/register", body);
      assert.equal(res.status, 422);
      assert.equal(res.body.status, "error");
      assert.ok(res.body.errors.includes(message), JSON.stringify(res.body));
    });
  }

  test("login without fields returns 422", async () => {
    const res = await ctx.request("POST", "/api/auth/login", { email: "a@b.co" });
    assert.equal(res.status, 422);
  });

  test("malformed JSON returns 400 with a structured error", async () => {
    const res = await ctx.request("POST", "/api/auth/login", "{bad json");
    assert.equal(res.status, 400);
    assert.deepEqual(res.body, { status: "error", errors: ["Malformed JSON body"] });
  });

  test("unknown route returns structured 404", async () => {
    const res = await ctx.request("GET", "/api/nope");
    assert.equal(res.status, 404);
    assert.equal(res.body.status, "error");
  });

  test("CORS allows only the configured frontend origin", async () => {
    const allowed = await fetch(`${ctx.base}/api/health`, { headers: { origin: "http://localhost:5173" } });
    assert.equal(allowed.headers.get("access-control-allow-origin"), "http://localhost:5173");
    const denied = await fetch(`${ctx.base}/api/health`, { headers: { origin: "http://evil.example" } });
    assert.equal(denied.headers.get("access-control-allow-origin"), null);
  });

  test("security headers from helmet are present", async () => {
    const res = await fetch(`${ctx.base}/api/health`);
    assert.equal(res.headers.get("x-content-type-options"), "nosniff");
    assert.equal(res.headers.get("x-powered-by"), null);
  });
});

describe("database failures are handled gracefully", () => {
  test("no database configured: health 200, auth routes 503", async () => {
    const ctx = await startApp({ pool: null });
    try {
      const health = await ctx.request("GET", "/api/health");
      assert.equal(health.status, 200);
      assert.equal(health.body.database, "not_configured");
      const reg = await ctx.request("POST", "/api/auth/register", USER);
      assert.equal(reg.status, 503);
      const log = await ctx.request("POST", "/api/auth/login", USER);
      assert.equal(log.status, 503);
    } finally {
      await ctx.close();
    }
  });

  test("database unreachable: health 200 'unavailable', auth routes 503, no internal details leaked", async () => {
    const down = {
      query: async () => {
        const err = new Error("connect ECONNREFUSED 10.0.0.1:5432");
        err.code = "ECONNREFUSED";
        throw err;
      },
    };
    const ctx = await startApp({ pool: down });
    try {
      const health = await ctx.request("GET", "/api/health");
      assert.equal(health.status, 200);
      assert.equal(health.body.database, "unavailable");
      const res = await ctx.request("POST", "/api/auth/login", USER);
      assert.equal(res.status, 503);
      assert.ok(!JSON.stringify(res.body).includes("10.0.0.1"));
    } finally {
      await ctx.close();
    }
  });
});
