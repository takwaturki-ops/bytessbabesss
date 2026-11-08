// MVP integration tests: backend (in-memory PostgreSQL via pg-mem) + the REAL AI service over HTTP.
// Requires the AI service running (default http://localhost:8001, or AI_SERVICE_URL). Skipped otherwise.
import assert from "node:assert/strict";
import { after, before, describe, test } from "node:test";

import bcrypt from "bcrypt";

import { createAiClient } from "../src/services/aiClient.js";
import { createMemoryPool, startApp } from "./helpers.js";

const AI_URL = process.env.AI_SERVICE_URL || "http://localhost:8001";
const ai = createAiClient({ baseUrl: AI_URL, apiKey: process.env.INTERNAL_API_KEY || "", timeoutMs: 30000 });
let aiUp = false;
try {
  aiUp = (await ai.health()).status === 200;
} catch { aiUp = false; }
const live = { skip: aiUp ? false : `AI service not reachable at ${AI_URL}` };

async function registerAndLogin(ctx, email, name = "Test User") {
  await ctx.request("POST", "/api/auth/register", { name, email, password: "password-123" });
  const res = await ctx.request("POST", "/api/auth/login", { email, password: "password-123" });
  return { authorization: `Bearer ${res.body.data.accessToken}` };
}

describe("MVP API with the real AI service", live, () => {
  let ctx;
  let user;
  let admin;
  before(async () => {
    const pool = createMemoryPool();
    await pool.query("INSERT INTO users (name, email, password_hash, role) VALUES ('Admin', 'admin@9antra.tn', $1, 'admin')",
      [await bcrypt.hash("admin-pass-123", 4)]);
    ctx = await startApp({ pool, ai });
    user = await registerAndLogin(ctx, "user@example.com", "Amina");
    const res = await ctx.request("POST", "/api/auth/login", { email: "admin@9antra.tn", password: "admin-pass-123" });
    admin = { authorization: `Bearer ${res.body.data.accessToken}` };
  });
  after(async () => ctx && ctx.close());

  test("health reports database and AI service", async () => {
    const res = await ctx.request("GET", "/api/health");
    assert.equal(res.status, 200);
    assert.equal(res.body.database, "connected");
    assert.match(res.body.ai_service, /^up/);
  });

  test("course catalog lists the 12 seeded courses with AI catalog prices", async () => {
    const res = await ctx.request("GET", "/api/courses");
    assert.equal(res.status, 200);
    assert.equal(res.body.data.length, 12);
    const c3 = (await ctx.request("GET", "/api/courses/C003")).body.data;
    assert.equal(c3.priceTnd, 349);
    assert.equal((await ctx.request("GET", "/api/courses/NOPE")).status, 404);
  });

  test("chat: Sales Agent answers, messages persist, history reopens", async () => {
    const conv = await ctx.request("POST", "/api/conversations", {}, user);
    assert.equal(conv.status, 201);
    const id = conv.body.data.id;
    const sent = await ctx.request("POST", `/api/conversations/${id}/messages`, { content: "I want to learn machine learning" }, user);
    assert.equal(sent.status, 201, JSON.stringify(sent.body));
    const meta = sent.body.data.assistantMessage.metadata;
    assert.equal(meta.agent, "sales_agent");
    assert.ok(meta.recommended_courses.some((c) => c.course_id === "C003"));
    await ctx.request("POST", `/api/conversations/${id}/messages`, { content: "C'est trop cher pour moi." }, user);
    const history = await ctx.request("GET", `/api/conversations/${id}/messages`, undefined, user);
    assert.equal(history.body.data.messages.length, 4);
    assert.deepEqual(history.body.data.messages.map((m) => m.role), ["user", "assistant", "user", "assistant"]);
    assert.equal(history.body.data.messages[3].metadata.detected_intent, "price_objection");
    const list = await ctx.request("GET", "/api/conversations", undefined, user);
    assert.equal(list.body.data[0].title, "I want to learn machine learning");
  });

  test("conversations are private to their owner", async () => {
    const other = await registerAndLogin(ctx, "other@example.com");
    const res = await ctx.request("GET", "/api/conversations/1/messages", undefined, other);
    assert.equal(res.status, 404);
  });

  test("purchase approved: five agents run, order paid, transaction confirmed, revenue counted once", async () => {
    const res = await ctx.request("POST", "/api/purchases", { course_id: "C003", payment_scenario: "success", conversation_id: 1 }, user);
    assert.equal(res.status, 201, JSON.stringify(res.body));
    const d = res.body.data;
    assert.equal(d.finalStatus, "completed");
    assert.equal(d.purchaseConfirmed, true);
    assert.equal(d.amountTnd, 349);
    assert.deepEqual(d.trace.map((t) => t.name), ["Sales conversation", "Customer insights", "Order creation",
      "Fraud screening", "Payment validation", "Financial update"]);
    assert.equal(d.agents.fraud.action, "allow");
    assert.equal(d.agents.payment.confirmed, true);
    assert.ok(d.agents.customerIntelligence.sentiment);
    assert.equal(d.agents.financial.countedAsRevenue, true);

    const detail = await ctx.request("GET", `/api/purchases/${d.orderId}`, undefined, user);
    assert.equal(detail.body.data.order.status, "paid");
    assert.equal(detail.body.data.transaction.status, "success");
    assert.equal(detail.body.data.transaction.payment_confirmed, true);
    assert.equal(detail.body.data.trace.length, 6);
    assert.equal(detail.body.data.fraudAlert, null);

    const again = await ctx.request("POST", "/api/purchases", { course_id: "C003" }, user);
    assert.equal(again.status, 409, "a paid course cannot be bought twice");
  });

  test("purchase blocked by fraud: no payment, no transaction, alert created", async () => {
    const res = await ctx.request("POST", "/api/purchases", { course_id: "C002", payment_scenario: "invalid_signature" }, user);
    assert.equal(res.status, 201);
    assert.equal(res.body.data.finalStatus, "blocked_by_fraud");
    assert.equal(res.body.data.agents.payment, null);
    assert.equal(res.body.data.transactionId, null);
    const detail = (await ctx.request("GET", `/api/purchases/${res.body.data.orderId}`, undefined, user)).body.data;
    assert.equal(detail.order.status, "blocked");
    assert.equal(detail.transaction, null);
    assert.equal(detail.fraudAlert.action, "block");
  });

  test("purchase pending manual validation: awaiting approval, admin approves without a fake payment", async () => {
    const res = await ctx.request("POST", "/api/purchases", { course_id: "C005", payment_scenario: "suspicious_location" }, user);
    assert.equal(res.body.data.finalStatus, "awaiting_human_approval");
    const orderId = res.body.data.orderId;
    const alerts = (await ctx.request("GET", "/api/admin/alerts", undefined, admin)).body.data;
    const alert = alerts.find((a) => a.orderId === orderId);
    assert.equal(alert.status, "open");
    const decision = await ctx.request("POST", `/api/admin/alerts/${alert.id}/decision`, { decision: "approve" }, admin);
    assert.equal(decision.status, 200);
    assert.equal(decision.body.data.orderStatus, "approved_awaiting_payment");
    const again = await ctx.request("POST", `/api/admin/alerts/${alert.id}/decision`, { decision: "reject" }, admin);
    assert.equal(again.status, 409);
  });

  test("failed and pending payments are recorded but never counted as revenue", async () => {
    const failed = await ctx.request("POST", "/api/purchases", { course_id: "C007", payment_scenario: "failed" }, user);
    assert.equal(failed.body.data.finalStatus, "payment_failed");
    const pending = await ctx.request("POST", "/api/purchases", { course_id: "C008", payment_scenario: "pending" }, user);
    assert.equal(pending.body.data.finalStatus, "payment_pending");
    const stats = (await ctx.request("GET", "/api/admin/stats", undefined, admin)).body.data;
    assert.equal(stats.revenue.totalTnd, 349);      // only the completed C003 purchase
    assert.equal(stats.revenue.paidOrders, 1);
    assert.equal(stats.orders.total, 5);
    assert.equal(stats.orders.byStatus.failed, 1);
    assert.equal(stats.orders.byStatus.pending, 1);
    assert.equal(stats.transactions.byStatus.success, 1);
  });

  test("real transaction history reaches the fraud agent (repeated failures -> human approval)", async () => {
    const buyer = await registerAndLogin(ctx, "retry@example.com");
    for (let i = 0; i < 3; i += 1) {
      const r = await ctx.request("POST", "/api/purchases", { course_id: "C004", payment_scenario: "failed" }, buyer);
      assert.equal(r.body.data.finalStatus, "payment_failed");
    }
    const fourth = await ctx.request("POST", "/api/purchases", { course_id: "C004", payment_scenario: "success" }, buyer);
    assert.equal(fourth.body.data.finalStatus, "awaiting_human_approval");
    assert.ok(fourth.body.data.agents.fraud.flags.includes("REPEATED_ATTEMPTS"));
  });

  test("admin endpoints: insights from the Financial Analyst Agent on DB data, users, orders, activity", async () => {
    const insights = await ctx.request("GET", "/api/admin/insights", undefined, admin);
    assert.equal(insights.status, 200, JSON.stringify(insights.body));
    assert.equal(insights.body.data.metrics.gross_revenue_tnd, 349);
    assert.ok(insights.body.data.narrative);
    assert.ok((await ctx.request("GET", "/api/admin/users", undefined, admin)).body.data.length >= 4);
    assert.ok((await ctx.request("GET", "/api/admin/orders", undefined, admin)).body.data.length >= 8);
    const activity = (await ctx.request("GET", "/api/admin/agent-activity", undefined, admin)).body.data;
    assert.ok(activity.some((e) => e.agent === "fraud_agent") && activity.some((e) => e.agent === "payment_agent"));
  });

  test("admin course management keeps prices aligned with the AI catalog", async () => {
    const upd = await ctx.request("PATCH", "/api/admin/courses/C012", { is_active: false }, admin);
    assert.equal(upd.body.data.isActive, false);
    assert.equal((await ctx.request("GET", "/api/courses")).body.data.length, 11);
    const price = await ctx.request("PATCH", "/api/admin/courses/C012", { price_tnd: 1 }, admin);
    assert.equal(price.status, 422);
  });

  test("admin access is enforced by the backend", async () => {
    assert.equal((await ctx.request("GET", "/api/admin/stats", undefined, user)).status, 403);
    assert.equal((await ctx.request("GET", "/api/admin/stats")).status, 401);
    const reg = await ctx.request("POST", "/api/auth/register", { name: "Mallory", email: "m@example.com", password: "password-123", role: "admin" });
    assert.equal(reg.body.data.user.role, "customer");
  });
});

describe("AI service unavailable (real network failure, closed port)", () => {
  test("purchase fails closed: 503, no order created", async () => {
    const pool = createMemoryPool();
    const ctx = await startApp({ pool, ai: createAiClient({ baseUrl: "http://127.0.0.1:9", timeoutMs: 2000 }) });
    try {
      const auth = await registerAndLogin(ctx, "down@example.com");
      const res = await ctx.request("POST", "/api/purchases", { course_id: "C001" }, auth);
      assert.equal(res.status, 503);
      const { rows } = await pool.query("SELECT COUNT(*)::int AS n FROM orders");
      assert.equal(rows[0].n, 0);
      const conv = await ctx.request("POST", "/api/conversations", {}, auth);
      const chat = await ctx.request("POST", `/api/conversations/${conv.body.data.id}/messages`, { content: "hello" }, auth);
      assert.equal(chat.status, 503);
    } finally {
      await ctx.close();
    }
  });
});
