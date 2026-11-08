// Two-factor authentication (TOTP) tests, in-memory PostgreSQL via pg-mem.
import assert from "node:assert/strict";
import { after, before, describe, test } from "node:test";

import { currentCode, verifyCode } from "../src/services/2faService.js";
import { startApp } from "./helpers.js";

const USER = { name: "Salma Trabelsi", email: "salma@example.com", password: "s3cure-passw0rd" };
const STEP_MS = 30_000;

describe("2FA service", () => {
  const secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP";

  test("accepts the current code and refuses a wrong or malformed one", () => {
    const now = Date.now();
    assert.notEqual(verifyCode(currentCode(secret, now), secret, { timestamp: now }), null);
    assert.equal(verifyCode(currentCode(secret, now - 10 * STEP_MS), secret, { timestamp: now }), null);
    assert.equal(verifyCode("12345", secret), null);
    assert.equal(verifyCode("abcdef", secret), null);
    assert.equal(verifyCode(undefined, secret), null);
  });

  test("tolerates one step of clock drift, not more", () => {
    const now = Date.now();
    assert.notEqual(verifyCode(currentCode(secret, now - STEP_MS), secret, { timestamp: now }), null);
    assert.equal(verifyCode(currentCode(secret, now - 3 * STEP_MS), secret, { timestamp: now }), null);
  });

  test("refuses a code whose time step was already used", () => {
    const now = Date.now();
    const step = verifyCode(currentCode(secret, now), secret, { timestamp: now });
    assert.equal(verifyCode(currentCode(secret, now), secret, { timestamp: now, lastStep: step }), null);
  });
});

describe("2FA API", () => {
  let ctx;
  let token;
  let secret;
  let enableCode;

  before(async () => {
    ctx = await startApp();
    await ctx.request("POST", "/api/auth/register", USER);
  });
  after(async () => {
    await ctx.close();
  });

  const auth = (t) => ({ authorization: `Bearer ${t}` });
  const login = () => ctx.request("POST", "/api/auth/login", { email: USER.email, password: USER.password });
  const loginCode = (challengeToken, code) => ctx.request("POST", "/api/auth/login/2fa", { challengeToken, code });
  const nextCode = () => currentCode(secret, Date.now() + STEP_MS);

  test("without 2FA, login returns an access token directly", async () => {
    const res = await login();
    assert.equal(res.status, 200);
    assert.ok(res.body.data.accessToken);
    token = res.body.data.accessToken;
    const me = await ctx.request("GET", "/api/auth/me", undefined, auth(token));
    assert.equal(me.body.data.twoFactorEnabled, false);
  });

  test("setup returns a QR code and secret but does not turn 2FA on", async () => {
    const res = await ctx.request("POST", "/api/auth/2fa/setup", {}, auth(token));
    assert.equal(res.status, 200);
    assert.match(res.body.data.qrCodeDataUrl, /^data:image\/png;base64,/);
    assert.match(res.body.data.otpauthUrl, /^otpauth:\/\/totp\/9antra:/);
    secret = res.body.data.secret;
    assert.match(secret, /^[A-Z2-7]+$/);

    const again = await login();
    assert.ok(again.body.data.accessToken, "pending setup must not require a code yet");
  });

  test("setup requires authentication", async () => {
    const res = await ctx.request("POST", "/api/auth/2fa/setup", {});
    assert.equal(res.status, 401);
  });

  test("enable refuses a wrong code and accepts the app's code", async () => {
    const wrong = currentCode(secret, Date.now() - 10 * STEP_MS);
    const bad = await ctx.request("POST", "/api/auth/2fa/enable", { code: wrong }, auth(token));
    assert.equal(bad.status, 400);

    enableCode = currentCode(secret);
    const ok = await ctx.request("POST", "/api/auth/2fa/enable", { code: enableCode }, auth(token));
    assert.equal(ok.status, 200);
    assert.equal(ok.body.data.twoFactorEnabled, true);

    const me = await ctx.request("GET", "/api/auth/me", undefined, auth(token));
    assert.equal(me.body.data.twoFactorEnabled, true);
    assert.ok(!JSON.stringify(me.body).includes(secret), "the secret is never sent back");
  });

  test("setup is refused once 2FA is enabled (the secret cannot be replaced or read again)", async () => {
    const res = await ctx.request("POST", "/api/auth/2fa/setup", {}, auth(token));
    assert.equal(res.status, 409);
  });

  test("with 2FA, the password alone gives no access token", async () => {
    const res = await login();
    assert.equal(res.status, 200);
    assert.equal(res.body.data.twoFactorRequired, true);
    assert.ok(res.body.data.challengeToken);
    assert.equal(res.body.data.accessToken, undefined);

    const me = await ctx.request("GET", "/api/auth/me", undefined, auth(res.body.data.challengeToken));
    assert.equal(me.status, 401, "the challenge token is not an access token");
  });

  test("the code used to enable 2FA cannot be replayed at login", async () => {
    const { challengeToken } = (await login()).body.data;
    const res = await loginCode(challengeToken, enableCode);
    assert.equal(res.status, 401);
  });

  test("a valid code completes login, and cannot be used twice", async () => {
    const code = nextCode();
    const first = await loginCode((await login()).body.data.challengeToken, code);
    assert.equal(first.status, 200);
    const me = await ctx.request("GET", "/api/auth/me", undefined, auth(first.body.data.accessToken));
    assert.equal(me.status, 200);
    assert.equal(me.body.data.email, USER.email);

    const second = await loginCode((await login()).body.data.challengeToken, code);
    assert.equal(second.status, 401);
  });

  test("a challenge is dropped after 5 wrong codes", async () => {
    await ctx.pool.query("UPDATE users SET totp_last_step = NULL WHERE email = $1", [USER.email]);
    const { challengeToken } = (await login()).body.data;
    const wrong = currentCode(secret, Date.now() - 10 * STEP_MS);
    for (let i = 0; i < 5; i += 1) {
      assert.equal((await loginCode(challengeToken, wrong)).status, 401);
    }
    const res = await loginCode(challengeToken, currentCode(secret));
    assert.equal(res.status, 401);
    assert.match(res.body.errors[0], /Too many attempts/);
  });

  test("a forged or expired challenge token is refused", async () => {
    const res = await loginCode("not-a-token", currentCode(secret));
    assert.equal(res.status, 401);
  });

  test("disable needs the password and a valid code, then login is one step again", async () => {
    // Codes of the current window were used above; start from a clean replay counter.
    await ctx.pool.query("UPDATE users SET totp_last_step = NULL WHERE email = $1", [USER.email]);

    const badPassword = await ctx.request("POST", "/api/auth/2fa/disable",
      { password: "wrong-password", code: currentCode(secret) }, auth(token));
    assert.equal(badPassword.status, 401);

    const badCode = await ctx.request("POST", "/api/auth/2fa/disable",
      { password: USER.password, code: currentCode(secret, Date.now() - 10 * STEP_MS) }, auth(token));
    assert.equal(badCode.status, 400);

    const ok = await ctx.request("POST", "/api/auth/2fa/disable",
      { password: USER.password, code: currentCode(secret) }, auth(token));
    assert.equal(ok.status, 200);
    assert.equal(ok.body.data.twoFactorEnabled, false);

    const { rows } = await ctx.pool.query("SELECT totp_secret, totp_enabled FROM users WHERE email = $1", [USER.email]);
    assert.equal(rows[0].totp_enabled, false);
    assert.equal(rows[0].totp_secret, null);

    const res = await login();
    assert.ok(res.body.data.accessToken);
  });
});
