// Rate limiting tests (small limits so they run fast). In-memory PostgreSQL via pg-mem.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { startApp } from "./helpers.js";

const big = { windowMs: 60_000, limit: 1000 };
const small = (limit) => ({ windowMs: 60_000, limit });
// Everything generous unless a test narrows one limiter.
const limits = (overrides) => ({
  api: big, login: big, loginAccount: big, twoFactor: big, register: big, twoFactorSettings: big, ...overrides,
});

const USER = { name: "Rania Gharbi", email: "rania@example.com", password: "s3cure-passw0rd" };
const fromIp = (ip) => ({ "x-forwarded-for": ip });

async function withApp(options, fn) {
  const ctx = await startApp(options);
  try {
    await fn(ctx);
  } finally {
    await ctx.close();
  }
}

describe("rate limiting", () => {
  test("failed logins per IP: blocked after the limit, with 429 + Retry-After + RateLimit headers", async () => {
    await withApp({ rateLimits: limits({ login: small(3) }) }, async (ctx) => {
      await ctx.request("POST", "/api/auth/register", USER);
      for (let i = 0; i < 3; i += 1) {
        const res = await ctx.request("POST", "/api/auth/login", { email: USER.email, password: "wrong-password" });
        assert.equal(res.status, 401);
      }
      const blocked = await ctx.request("POST", "/api/auth/login", { email: USER.email, password: USER.password });
      assert.equal(blocked.status, 429, "even the right password is refused while blocked");
      assert.equal(blocked.body.status, "error");
      assert.match(blocked.body.errors[0], /Too many failed login attempts\. Try again in \d+ minute/);
      assert.ok(Number(blocked.headers.get("retry-after")) > 0);
      assert.ok(blocked.headers.get("ratelimit"), "standard RateLimit header");

      const otherIp = await ctx.request("POST", "/api/auth/login", USER, fromIp("203.0.113.7"));
      assert.equal(otherIp.status, 200, "another client is not affected");
    });
  });

  test("successful logins are not counted", async () => {
    await withApp({ rateLimits: limits({ login: small(2), loginAccount: small(2) }) }, async (ctx) => {
      await ctx.request("POST", "/api/auth/register", USER);
      for (let i = 0; i < 5; i += 1) {
        const res = await ctx.request("POST", "/api/auth/login", USER);
        assert.equal(res.status, 200);
      }
    });
  });

  test("failed logins per account: one account attacked from many IPs is blocked, others are not", async () => {
    await withApp({ rateLimits: limits({ loginAccount: small(3) }) }, async (ctx) => {
      await ctx.request("POST", "/api/auth/register", USER);
      for (let i = 0; i < 3; i += 1) {
        const res = await ctx.request("POST", "/api/auth/login",
          { email: USER.email, password: "wrong-password" }, fromIp(`198.51.100.${i + 1}`));
        assert.equal(res.status, 401);
      }
      const blocked = await ctx.request("POST", "/api/auth/login",
        { email: ` ${USER.email.toUpperCase()} `, password: USER.password }, fromIp("198.51.100.50"));
      assert.equal(blocked.status, 429, "same account, any spelling, any IP");
      assert.match(blocked.body.errors[0], /for this account/);

      const other = await ctx.request("POST", "/api/auth/login",
        { email: "someone.else@example.com", password: "whatever-pass" }, fromIp("198.51.100.50"));
      assert.equal(other.status, 401, "other accounts still get a normal answer");
    });
  });

  test("X-Forwarded-For is ignored when no proxy is trusted (cannot be spoofed)", async () => {
    await withApp({ trustProxy: false, rateLimits: limits({ login: small(2) }) }, async (ctx) => {
      for (let i = 0; i < 2; i += 1) {
        await ctx.request("POST", "/api/auth/login", { email: `x${i}@example.com`, password: "wrong-password" }, fromIp(`192.0.2.${i}`));
      }
      const res = await ctx.request("POST", "/api/auth/login", { email: "y@example.com", password: "wrong-password" }, fromIp("192.0.2.99"));
      assert.equal(res.status, 429);
    });
  });

  test("registration: only created accounts count", async () => {
    await withApp({ rateLimits: limits({ register: small(2) }) }, async (ctx) => {
      for (let i = 0; i < 4; i += 1) {
        const invalid = await ctx.request("POST", "/api/auth/register", { name: "A", email: "bad", password: "x" });
        assert.equal(invalid.status, 422);
      }
      for (let i = 0; i < 2; i += 1) {
        const ok = await ctx.request("POST", "/api/auth/register", { ...USER, email: `user${i}@example.com` });
        assert.equal(ok.status, 201);
      }
      const blocked = await ctx.request("POST", "/api/auth/register", { ...USER, email: "user9@example.com" });
      assert.equal(blocked.status, 429);
      assert.match(blocked.body.errors[0], /Too many accounts/);
    });
  });

  test("wrong 2FA codes per IP are limited", async () => {
    await withApp({ rateLimits: limits({ twoFactor: small(2) }) }, async (ctx) => {
      for (let i = 0; i < 2; i += 1) {
        const res = await ctx.request("POST", "/api/auth/login/2fa", { challengeToken: "bad", code: "123456" });
        assert.equal(res.status, 401);
      }
      const blocked = await ctx.request("POST", "/api/auth/login/2fa", { challengeToken: "bad", code: "123456" });
      assert.equal(blocked.status, 429);
      assert.match(blocked.body.errors[0], /Too many wrong codes/);
    });
  });

  test("the whole API has a per-IP ceiling", async () => {
    await withApp({ rateLimits: limits({ api: small(3) }) }, async (ctx) => {
      for (let i = 0; i < 3; i += 1) {
        assert.equal((await ctx.request("GET", "/api/health")).status, 200);
      }
      const blocked = await ctx.request("GET", "/api/courses");
      assert.equal(blocked.status, 429);
      assert.match(blocked.body.errors[0], /Too many requests/);
    });
  });
});
