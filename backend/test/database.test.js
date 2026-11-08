// SSL choice for the PostgreSQL pool: off for local PostgreSQL, kept for Neon.
import assert from "node:assert/strict";
import { test } from "node:test";

import { sslFor } from "../src/config/database.js";

const NEON_SSL = { rejectUnauthorized: false };

test("local PostgreSQL connects without SSL", () => {
  assert.equal(sslFor("postgresql://postgres:pw@localhost:5432/9antra"), false);
  assert.equal(sslFor("postgresql://postgres:pw@127.0.0.1:5432/9antra"), false);
  assert.equal(sslFor("postgresql://postgres:pw@[::1]:5432/9antra"), false);
});

test("local PostgreSQL keeps SSL when the URL asks for it", () => {
  assert.deepEqual(sslFor("postgresql://postgres:pw@localhost/9antra?sslmode=require"), NEON_SSL);
});

test("Neon keeps the original SSL setting", () => {
  assert.deepEqual(sslFor("postgresql://u:pw@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require"), NEON_SSL);
  assert.deepEqual(sslFor("postgresql://u:pw@ep-x.eu-central-1.aws.neon.tech/neondb"), NEON_SSL);
});

test("sslmode=disable turns SSL off for any host", () => {
  assert.equal(sslFor("postgresql://u:pw@db.example.com/app?sslmode=disable"), false);
});
