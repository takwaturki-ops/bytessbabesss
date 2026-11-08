// Pure helpers for the auth flow (no React, no axios) so they can be unit-tested with `node --test`.

export const TOKEN_KEY = "smartfin_token";

/**
 * Backend contract: POST /api/auth/login -> { status: "ok", data: { accessToken, tokenType: "Bearer" } }.
 * Throws when the token is missing, so a login can never "succeed" without a token.
 */
export function extractAccessToken(response) {
  const token = response?.data?.data?.accessToken;
  if (typeof token !== "string" || token.trim() === "") {
    throw new Error("Réponse du serveur invalide : jeton d'accès manquant.");
  }
  return token;
}

/** Backend errors are { status: "error", errors: ["..."] }. Returns a message safe to display. */
export function getErrorMessage(error, fallback = "Une erreur est survenue.") {
  const data = error?.response?.data;
  if (Array.isArray(data?.errors) && data.errors.length) {
    return data.errors.join(" ");
  }
  if (typeof data?.error === "string" && data.error) {
    return data.error;
  }
  if (error?.response?.status === 503) {
    return "Service momentanément indisponible. Réessayez plus tard.";
  }
  if (error?.isAxiosError && !error.response) {
    return "Impossible de joindre le serveur. Vérifiez qu'il est démarré.";
  }
  if (!error?.isAxiosError && error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

/** Read the stored token; cleans up values left by the previous bug ("undefined"/"null" strings). */
export function readToken(storage) {
  const token = storage?.getItem(TOKEN_KEY) ?? null;
  if (!token || token === "undefined" || token === "null") {
    storage?.removeItem(TOKEN_KEY);
    return null;
  }
  return token;
}

export function writeToken(storage, token) {
  if (typeof token !== "string" || !token) {
    throw new Error("Refus d'enregistrer un jeton vide.");
  }
  storage.setItem(TOKEN_KEY, token);
}

export function clearToken(storage) {
  storage?.removeItem(TOKEN_KEY);
}

/** Normalize the configured API origin (no trailing slash). */
export function resolveApiBaseUrl(value, fallback = "http://localhost:4000") {
  return (value || fallback).replace(/\/+$/, "");
}
