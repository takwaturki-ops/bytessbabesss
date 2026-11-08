import speakeasy from "speakeasy";

/*
 * TOTP helpers (ported to ESM). NOT wired into login yet: real 2FA needs a per-user secret stored in the
 * database, an enrolment flow (QR code), verification at login and a way to disable it.
 * The previous login check used one global secret for every user, which is not two-factor authentication.
 */
export const generateSecret = () => speakeasy.generateSecret({
  name: "SmartFin AI",
});

export const verifyToken = (token, secret) => speakeasy.totp.verify({
  token,
  secret,
  encoding: "base32",
});
