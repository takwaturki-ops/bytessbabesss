// Startup tests: run the real entry point (src/server.js) as a child process, exactly like `npm start`.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const backendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function startServer(env) {
  const child = spawn(process.execPath, ["src/server.js"], {
    cwd: backendDir,
    // Clean environment: no inherited DATABASE_URL / JWT_SECRET from the developer's shell.
    // The keys are set to "" because dotenv never overrides an existing variable: this keeps
    // backend/.env (the developer's real config) from leaking into these tests.
    env: {
      PATH: process.env.PATH,
      SystemRoot: process.env.SystemRoot,
      JWT_SECRET: "",
      DATABASE_URL: "",
      USE_IN_MEMORY_DB: "",
      ...env,
    },
  });
  let output = "";
  child.stdout.on("data", (d) => { output += d; });
  child.stderr.on("data", (d) => { output += d; });
  const exited = new Promise((resolve) => child.on("exit", (code) => resolve(code)));
  return { child, exited, output: () => output };
}

async function waitForHealth(port, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/health`);
      return { status: res.status, body: await res.json() };
    } catch {
      await new Promise((r) => setTimeout(r, 200));
    }
  }
  throw new Error("server did not answer in time");
}

test("server refuses to start without JWT_SECRET (no default secret)", async () => {
  const srv = startServer({ PORT: "4601" });
  const code = await srv.exited;
  assert.equal(code, 1);
  assert.match(srv.output(), /JWT_SECRET is required/);
});

test("server starts with JWT_SECRET and /api/health returns 200 (database not configured)", async () => {
  const srv = startServer({ PORT: "4602", JWT_SECRET: "x".repeat(40) });
  try {
    const res = await waitForHealth(4602);
    assert.equal(res.status, 200);
    assert.equal(res.body.status, "success");
    assert.equal(res.body.database, "not_configured");
  } finally {
    srv.child.kill();
    await srv.exited;
  }
});

test("server still starts when the database is unreachable", async () => {
  const srv = startServer({
    PORT: "4603",
    JWT_SECRET: "x".repeat(40),
    DATABASE_URL: "postgresql://user:pass@127.0.0.1:9/nodb",
  });
  try {
    const res = await waitForHealth(4603);
    assert.equal(res.status, 200);
    assert.equal(res.body.database, "unavailable");
    assert.doesNotMatch(srv.output(), /pass@/, "connection string must not be logged");
  } finally {
    srv.child.kill();
    await srv.exited;
  }
});
