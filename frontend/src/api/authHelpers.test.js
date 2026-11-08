// Run with: npm test   (Node built-in test runner, no extra dependency)
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  TOKEN_KEY,
  clearToken,
  extractAccessToken,
  extractTwoFactorChallenge,
  normalizeOtp,
  getErrorMessage,
  readToken,
  resolveApiBaseUrl,
  writeToken,
} from "./authHelpers.js";

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    removeItem: (k) => { delete data[k]; },
    dump: () => ({ ...data }),
  };
}

test("login reads the token from data.accessToken (backend contract)", () => {
  const response = { data: { status: "ok", data: { accessToken: "abc.def.ghi", tokenType: "Bearer" } } };
  assert.equal(extractAccessToken(response), "abc.def.ghi");
});

test("login fails when the token is missing or in the old field", () => {
  for (const response of [
    { data: { status: "ok", data: {} } },
    { data: { token: "old-field-not-used" } },
    { data: { status: "ok", data: { accessToken: "" } } },
    undefined,
  ]) {
    assert.throws(() => extractAccessToken(response), /jeton d'accès manquant/);
  }
});

test("invalid credentials show the backend error message", () => {
  const err = { isAxiosError: true, response: { status: 401, data: { status: "error", errors: ["Invalid email or password"] } } };
  assert.equal(getErrorMessage(err, "fallback"), "Invalid email or password");
});

test("registration validation errors are all displayed", () => {
  const err = { isAxiosError: true, response: { status: 422, data: { errors: ["Email format is invalid", "Password must be at least 8 characters"] } } };
  assert.equal(getErrorMessage(err), "Email format is invalid Password must be at least 8 characters");
});

test("duplicate registration (409) shows the backend message", () => {
  const err = { isAxiosError: true, response: { status: 409, data: { errors: ["Email is already registered"] } } };
  assert.equal(getErrorMessage(err), "Email is already registered");
});

test("network and service errors have readable messages", () => {
  assert.match(getErrorMessage({ isAxiosError: true, request: {} }), /Impossible de joindre le serveur/);
  assert.match(getErrorMessage({ isAxiosError: true, response: { status: 503, data: {} } }), /indisponible/);
  assert.equal(getErrorMessage(new Error("Réponse du serveur invalide : jeton d'accès manquant.")),
    "Réponse du serveur invalide : jeton d'accès manquant.");
  assert.equal(getErrorMessage({}, "fallback"), "fallback");
});

test("token is stored and read consistently under one key", () => {
  const storage = memoryStorage();
  writeToken(storage, "jwt-123");
  assert.deepEqual(storage.dump(), { [TOKEN_KEY]: "jwt-123" });
  assert.equal(readToken(storage), "jwt-123");
  clearToken(storage);
  assert.equal(readToken(storage), null);
});

test("empty tokens are never stored, and legacy 'undefined' values are cleaned up", () => {
  const storage = memoryStorage();
  assert.throws(() => writeToken(storage, undefined));
  assert.throws(() => writeToken(storage, ""));
  for (const legacy of ["undefined", "null"]) {
    const s = memoryStorage({ [TOKEN_KEY]: legacy });
    assert.equal(readToken(s), null);
    assert.deepEqual(s.dump(), {});
  }
});

test("API base URL comes from configuration, without trailing slash", () => {
  assert.equal(resolveApiBaseUrl("https://api.example.com/"), "https://api.example.com");
  assert.equal(resolveApiBaseUrl(undefined), "http://localhost:4000");
});

test("2FA: a login answer with twoFactorRequired gives the challenge token", () => {
  assert.equal(extractTwoFactorChallenge({ data: { status: "ok", data: { twoFactorRequired: true, challengeToken: "c.t.k" } } }), "c.t.k");
  assert.equal(extractTwoFactorChallenge({ data: { status: "ok", data: { accessToken: "a.b.c" } } }), null);
  assert.throws(() => extractTwoFactorChallenge({ data: { data: { twoFactorRequired: true } } }), /session de vérification/);
});

test("2FA: codes keep only 6 digits", () => {
  assert.equal(normalizeOtp("123 456"), "123456");
  assert.equal(normalizeOtp("12a34-5678"), "123456");
  assert.equal(normalizeOtp(undefined), "");
});
