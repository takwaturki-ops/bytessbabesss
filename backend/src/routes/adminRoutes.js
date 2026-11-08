import express from "express";

import { AiServiceError } from "../services/aiClient.js";
import { listOrders, orderDetail } from "../services/purchaseService.js";
import { asyncHandler, fail, iso, money, ok } from "../utils/http.js";
import { courseView } from "./courseRoutes.js";

const COURSE_COLUMNS = "id, title, title_ar, category, level, price_tnd, duration_hours, duration_weeks, description, is_active, created_at";

export function createAdminRouter({ pool, ai }) {
  const router = express.Router();

  // ---------------------------------------------------------------- statistics (computed from the database)
  router.get("/stats", asyncHandler(async (req, res) => {
    const [users, courses, orders, txs, alerts] = await Promise.all([
      pool.query("SELECT role FROM users"),
      pool.query("SELECT id, title, is_active FROM courses"),
      pool.query("SELECT id, course_id, amount_tnd, status, created_at FROM orders"),
      pool.query("SELECT status FROM transactions"),
      pool.query("SELECT status, action FROM fraud_alerts"),
    ]);
    const count = (rows, key) => rows.reduce((acc, r) => ({ ...acc, [r[key]]: (acc[r[key]] || 0) + 1 }), {});
    const paid = orders.rows.filter((o) => o.status === "paid"); // only confirmed payments are revenue
    const revenue = money(paid.reduce((s, o) => s + Number(o.amount_tnd), 0));
    const titles = Object.fromEntries(courses.rows.map((c) => [c.id, c.title]));
    const byCourse = {};
    const byDay = {};
    for (const o of paid) {
      byCourse[o.course_id] = (byCourse[o.course_id] || 0) + Number(o.amount_tnd);
      const day = iso(o.created_at).slice(0, 10);
      byDay[day] = (byDay[day] || 0) + Number(o.amount_tnd);
    }
    return ok(res, {
      users: { total: users.rows.length, byRole: count(users.rows, "role") },
      courses: { total: courses.rows.length, active: courses.rows.filter((c) => c.is_active).length },
      orders: { total: orders.rows.length, byStatus: count(orders.rows, "status") },
      transactions: { total: txs.rows.length, byStatus: count(txs.rows, "status") },
      fraudAlerts: { total: alerts.rows.length, open: alerts.rows.filter((a) => a.status === "open").length, byAction: count(alerts.rows, "action") },
      revenue: {
        totalTnd: revenue,
        paidOrders: paid.length,
        averageOrderTnd: paid.length ? money(revenue / paid.length) : 0,
        conversionRate: orders.rows.length ? Math.round((paid.length / orders.rows.length) * 10000) / 10000 : 0,
        byCourse: Object.entries(byCourse).map(([id, v]) => ({ courseId: id, title: titles[id] || id, revenueTnd: money(v) }))
          .sort((a, b) => b.revenueTnd - a.revenueTnd),
        byDay: Object.entries(byDay).map(([day, v]) => ({ day, revenueTnd: money(v) })).sort((a, b) => a.day.localeCompare(b.day)),
      },
      dataNotice: "SIMULATED payments - no real money is moved.",
    });
  }));

  // ---------------------------------------------------------------- Financial Analyst Agent on the real DB data
  router.get("/insights", asyncHandler(async (req, res) => {
    const [orders, txs] = await Promise.all([
      pool.query("SELECT id, course_id, amount_tnd, list_price_tnd, payment_method, status, created_at FROM orders"),
      pool.query("SELECT id, order_id, amount_tnd, status, failure_reason, created_at FROM transactions"),
    ]);
    const body = {
      question: "Summarize revenue, payment reliability and risks for the 9antra admin dashboard.",
      orders: orders.rows.map((o) => ({
        order_id: o.id, course_id: o.course_id, amount_tnd: money(o.amount_tnd), list_price_tnd: money(o.list_price_tnd),
        payment_method: o.payment_method, status: o.status, created_at: iso(o.created_at),
      })),
      transactions: txs.rows.map((t) => ({
        transaction_id: t.id, order_id: t.order_id, attempt_no: 1, status: t.status, amount_tnd: money(t.amount_tnd),
        failure_reason: t.failure_reason, created_at: iso(t.created_at),
      })),
    };
    try {
      const result = await ai.financial(body);
      if (result.status !== 200 || result.body?.status !== "ok") {
        return fail(res, 502, "Financial Analyst Agent returned an error", ...(result.body?.errors ?? []));
      }
      const { metrics, insights, narrative } = result.body.data;
      return ok(res, { metrics, insights, narrative, meta: { mode: result.body.meta?.mode, warnings: result.body.meta?.warnings } });
    } catch (err) {
      if (err instanceof AiServiceError) return fail(res, 503, "AI service unavailable");
      throw err;
    }
  }));

  // ---------------------------------------------------------------- users
  router.get("/users", asyncHandler(async (req, res) => {
    const { rows } = await pool.query(
      `SELECT u.id, u.name, u.email, u.role, u.created_at, COUNT(o.id)::int AS order_count
         FROM users u LEFT JOIN orders o ON o.user_id = u.id
        GROUP BY u.id, u.name, u.email, u.role, u.created_at ORDER BY u.id`,
    );
    return ok(res, rows.map((u) => ({ id: u.id, name: u.name, email: u.email, role: u.role, createdAt: iso(u.created_at), orderCount: u.order_count })));
  }));

  router.patch("/users/:id/role", asyncHandler(async (req, res) => {
    const id = Number(req.params.id);
    const role = req.body?.role;
    if (!Number.isInteger(id) || !["customer", "admin"].includes(role)) return fail(res, 422, "role must be 'customer' or 'admin'");
    if (id === req.auth.userId && role !== "admin") return fail(res, 409, "You cannot remove your own admin role");
    const { rows } = await pool.query("UPDATE users SET role = $1 WHERE id = $2 RETURNING id, name, email, role", [role, id]);
    if (!rows.length) return fail(res, 404, "User not found");
    return ok(res, rows[0]);
  }));

  // ---------------------------------------------------------------- courses (price stays aligned with the AI catalog)
  router.get("/courses", asyncHandler(async (req, res) => {
    const { rows } = await pool.query(`SELECT ${COURSE_COLUMNS} FROM courses ORDER BY id`);
    return ok(res, rows.map(courseView));
  }));

  router.patch("/courses/:id", asyncHandler(async (req, res) => {
    const { title, description, is_active: isActive, price_tnd: price } = req.body || {};
    if (price !== undefined) {
      return fail(res, 422, "price_tnd cannot be edited: prices come from the AI service catalog used by the purchase workflow");
    }
    const errors = [];
    if (title !== undefined && (typeof title !== "string" || !title.trim() || title.length > 200)) errors.push("title must be 1-200 characters");
    if (description !== undefined && (typeof description !== "string" || !description.trim())) errors.push("description must be a non-empty string");
    if (isActive !== undefined && typeof isActive !== "boolean") errors.push("is_active must be a boolean");
    if (title === undefined && description === undefined && isActive === undefined) errors.push("nothing to update");
    if (errors.length) return fail(res, 422, ...errors);

    const { rows: current } = await pool.query(`SELECT ${COURSE_COLUMNS} FROM courses WHERE id = $1`, [req.params.id]);
    if (!current.length) return fail(res, 404, "Course not found");
    const c = current[0];
    const { rows } = await pool.query(
      `UPDATE courses SET title = $1, description = $2, is_active = $3 WHERE id = $4 RETURNING ${COURSE_COLUMNS}`,
      [title?.trim() ?? c.title, description?.trim() ?? c.description, isActive ?? c.is_active, c.id],
    );
    return ok(res, courseView(rows[0]));
  }));

  // ---------------------------------------------------------------- orders
  router.get("/orders", asyncHandler(async (req, res) => ok(res, await listOrders(pool))));

  router.get("/orders/:id", asyncHandler(async (req, res) => {
    const detail = await orderDetail(pool, req.params.id);
    if (!detail) return fail(res, 404, "Order not found");
    return ok(res, detail);
  }));

  // ---------------------------------------------------------------- fraud alerts / human validation
  router.get("/alerts", asyncHandler(async (req, res) => {
    const { rows } = await pool.query(
      `SELECT a.id, a.order_id, a.action, a.risk_score, a.flags, a.explanation, a.status, a.reviewed_at, a.created_at,
              u.name AS user_name, u.email AS user_email, o.amount_tnd, o.course_id, o.status AS order_status
         FROM fraud_alerts a JOIN users u ON u.id = a.user_id JOIN orders o ON o.id = a.order_id
        ORDER BY a.created_at DESC`,
    );
    return ok(res, rows.map((a) => ({
      id: a.id, orderId: a.order_id, action: a.action, riskScore: a.risk_score, flags: a.flags ? a.flags.split(",") : [],
      explanation: a.explanation, status: a.status, reviewedAt: iso(a.reviewed_at), createdAt: iso(a.created_at),
      userName: a.user_name, userEmail: a.user_email, amountTnd: money(a.amount_tnd), courseId: a.course_id, orderStatus: a.order_status,
    })));
  }));

  // A human decision is recorded; it never fabricates a payment. Approved orders still need a new payment.
  router.post("/alerts/:id/decision", asyncHandler(async (req, res) => {
    const decision = req.body?.decision;
    if (!["approve", "reject"].includes(decision)) return fail(res, 422, "decision must be 'approve' or 'reject'");
    const { rows } = await pool.query("SELECT id, order_id, action, status FROM fraud_alerts WHERE id = $1", [Number(req.params.id)]);
    const alert = rows[0];
    if (!alert) return fail(res, 404, "Alert not found");
    if (alert.status !== "open") return fail(res, 409, `Alert already ${alert.status}`);
    if (decision === "approve" && alert.action === "block") return fail(res, 409, "Blocked transactions cannot be approved");

    const alertStatus = decision === "approve" ? "approved" : "rejected";
    const orderStatus = decision === "approve" ? "approved_awaiting_payment" : "rejected";
    await pool.query("UPDATE fraud_alerts SET status = $1, reviewed_by = $2, reviewed_at = NOW() WHERE id = $3", [alertStatus, req.auth.userId, alert.id]);
    await pool.query("UPDATE orders SET status = $1, updated_at = NOW() WHERE id = $2", [orderStatus, alert.order_id]);
    return ok(res, { alertId: alert.id, alertStatus, orderId: alert.order_id, orderStatus });
  }));

  // ---------------------------------------------------------------- AI agents activity (workflow traces)
  router.get("/agent-activity", asyncHandler(async (req, res) => {
    const { rows } = await pool.query(
      `SELECT e.order_id, e.step, e.name, e.agent, e.status, e.decision, e.summary, e.mode, e.duration_ms, e.created_at
         FROM agent_events e ORDER BY e.id DESC LIMIT 150`,
    );
    return ok(res, rows.map((e) => ({ ...e, created_at: iso(e.created_at) })));
  }));

  return router;
}
