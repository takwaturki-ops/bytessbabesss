import jwt from "jsonwebtoken";

const unauthorized = (res, message) => res.status(401).json({ status: "error", errors: [message] });

/**
 * Protect routes with a Bearer JWT.
 * Verifies signature (HS256 only) and expiry, then sets req.auth = { userId, role } from the token.
 */
export function createAuthMiddleware({ jwtSecret }) {
  if (!jwtSecret) {
    throw new Error("JWT_SECRET is required");
  }

  return function protect(req, res, next) {
    const [scheme, token] = (req.get("authorization") || "").split(" ");
    if (scheme !== "Bearer" || !token) {
      return unauthorized(res, "Authentication required");
    }

    let payload;
    try {
      payload = jwt.verify(token, jwtSecret, { algorithms: ["HS256"] });
    } catch (err) {
      return unauthorized(res, err.name === "TokenExpiredError" ? "Token expired" : "Invalid token");
    }

    const userId = Number(payload.sub);
    if (!Number.isInteger(userId) || userId <= 0) {
      return unauthorized(res, "Invalid token");
    }
    req.auth = { userId, role: payload.role };
    req.userId = userId; // kept for compatibility with the original controller
    return next();
  };
}
