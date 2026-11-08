// Small shared HTTP helpers (uniform JSON envelope used by every route).
export const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

export const ok = (res, data, status = 200) => res.status(status).json({ status: "ok", data });

export const fail = (res, status, ...errors) => res.status(status).json({ status: "error", errors });

const DB_UNAVAILABLE_CODES = new Set(["ECONNREFUSED", "ENOTFOUND", "ETIMEDOUT", "ECONNRESET", "57P01", "57P03"]);

export function isDbUnavailable(err) {
  return (
    DB_UNAVAILABLE_CODES.has(err?.code) ||
    (typeof err?.code === "string" && err.code.startsWith("08")) ||
    /timeout|terminated|connection/i.test(err?.message || "")
  );
}

/** PostgreSQL NUMERIC comes back as a string with node-postgres: convert money columns explicitly. */
export const money = (value) => (value === null || value === undefined ? null : Math.round(Number(value) * 100) / 100);

export const iso = (value) => (value instanceof Date ? value.toISOString() : value ? new Date(value).toISOString() : null);
