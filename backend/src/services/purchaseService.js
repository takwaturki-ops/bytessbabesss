// Backend side of the purchase workflow: builds the request for POST /workflow/purchase (AI service),
// then persists the result. The AI service orchestrates the five agents; the backend owns the database.
import { randomUUID } from "node:crypto";

import { customerIdFor, loadTurns } from "../routes/conversationRoutes.js";
import { iso, money } from "../utils/http.js";

// final_status (workflow/schemas.py FinalStatus) -> orders.status. Only "paid" counts as revenue.
export const ORDER_STATUS = {
  completed: "paid",
  payment_failed: "failed",
  payment_pending: "pending",
  payment_requires_review: "requires_review",
  awaiting_human_approval: "awaiting_approval",
  blocked_by_fraud: "blocked",
};

// PaymentScenario literal of the workflow (SIMULATED outcomes for the demo).
export const PAYMENT_SCENARIOS = ["success", "failed", "pending", "amount_mismatch", "duplicate",
  "repeated_attempts", "excessive_attempts", "invalid_signature", "suspicious_location"];
export const PAYMENT_METHODS = ["card", "mobile_wallet", "bank_transfer"];

const HISTORY_WINDOW_MS = 24 * 60 * 60 * 1000;

export const newWorkflowId = () => `WF-${randomUUID().replace(/-/g, "").slice(0, 12).toUpperCase()}`;

/** Recent transactions of this user, in the HistoryTxn format (status required, ISO timestamp with Z). */
export async function previousTransactions(pool, userId) {
  const { rows } = await pool.query(
    `SELECT t.id, t.order_id, t.amount_tnd, t.status, t.created_at, o.course_id
       FROM transactions t JOIN orders o ON o.id = t.order_id
      WHERE t.user_id = $1 ORDER BY t.created_at DESC LIMIT 100`,
    [userId],
  );
  const since = Date.now() - HISTORY_WINDOW_MS;
  return rows
    .filter((t) => new Date(t.created_at).getTime() >= since)
    .map((t) => ({
      transaction_id: t.id,
      order_id: t.order_id,
      customer_id: customerIdFor(userId),
      course_id: t.course_id,
      amount_tnd: money(t.amount_tnd),
      status: t.status,
      // The workflow stamps the current event with whole seconds; floor history to whole seconds too,
      // otherwise an attempt made in the same second looks "after" the event and the fraud rules ignore it.
      timestamp: new Date(Math.floor(new Date(t.created_at).getTime() / 1000) * 1000).toISOString(),
    }))
    .reverse();
}

export async function buildWorkflowRequest(pool, { userId, course, conversationId, message, paymentScenario, paymentMethod, discountCode }) {
  const body = {
    customer_id: customerIdFor(userId),
    message: message || `Je confirme l'achat du cours ${course.title}.`,
    course_id: course.id,
    confirm_purchase: true,
    payment_scenario: paymentScenario,
    payment_method: paymentMethod,
    previous_transactions: await previousTransactions(pool, userId),
    conversation_history: conversationId ? await loadTurns(pool, conversationId) : [],
    workflow_id: newWorkflowId(),
  };
  if (discountCode) body.discount_code = discountCode;
  return body;
}

/** Persist one workflow result atomically. Returns the stored order id (or null when no order was created). */
export async function persistWorkflowResult(pool, { userId, course, conversationId, request, result }) {
  if (!result.order_id) return null;
  const status = ORDER_STATUS[result.final_status];
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query(
      `INSERT INTO orders (id, user_id, course_id, conversation_id, workflow_id, amount_tnd, list_price_tnd,
                           payment_method, payment_scenario, status, final_status, next_step, workflow_result)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`,
      [result.order_id, userId, course.id, conversationId ?? null, result.workflow_id, result.amount_tnd,
        result.course?.price_tnd ?? money(course.price_tnd), request.payment_method, request.payment_scenario,
        status, result.final_status, result.next_step, JSON.stringify(result)],
    );

    const payment = result.payment_agent_result?.data;
    if (payment) { // the Payment Agent processed the simulated payment event
      await client.query(
        `INSERT INTO transactions (id, order_id, user_id, amount_tnd, status, payment_confirmed, failure_reason)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [result.transaction_id, result.order_id, userId, payment.amount_tnd ?? result.amount_tnd, payment.final_status,
          payment.payment_confirmed === true, payment.review_reasons?.join(", ") || null],
      );
    }

    const fraud = result.fraud_agent_result?.data;
    if (fraud && fraud.action !== "allow") {
      await client.query(
        `INSERT INTO fraud_alerts (order_id, user_id, action, risk_score, flags, explanation)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [result.order_id, userId, fraud.action, fraud.risk_score, (fraud.flags || []).join(","), fraud.explanation],
      );
    }

    for (const t of result.execution_trace || []) {
      await client.query(
        `INSERT INTO agent_events (order_id, step, name, agent, status, decision, summary, mode, duration_ms)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [result.order_id, t.step, t.name, t.agent, t.status, t.decision, t.summary, t.mode, t.duration_ms],
      );
    }
    await client.query("COMMIT");
    return result.order_id;
  } catch (err) {
    await client.query("ROLLBACK").catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

/** What the frontend shows: one short block per agent + the trace. */
export function summarizeWorkflow(result) {
  const d = (r) => (r && r.status === "ok" ? r.data : null);
  const sales = d(result.sales_agent_result);
  const intel = d(result.customer_intelligence_result);
  const fraud = d(result.fraud_agent_result);
  const payment = d(result.payment_agent_result);
  const impact = result.financial_impact;
  return {
    sales: sales && { intent: sales.detected_intent, nextAction: sales.next_action, reply: sales.reply },
    customerIntelligence: intel && {
      sentiment: intel.sentiment, interestScore: intel.interest_score, purchaseStage: intel.purchase_stage,
      objections: intel.objections, summary: intel.summary,
    },
    fraud: fraud && {
      action: fraud.action, riskScore: fraud.risk_score, riskLevel: fraud.risk_level, flags: fraud.flags,
      explanation: fraud.explanation,
    },
    payment: payment && {
      finalStatus: payment.final_status, confirmed: payment.payment_confirmed, customerMessage: payment.customer_message,
      reviewReasons: payment.review_reasons,
    },
    financial: impact && {
      countedAsRevenue: impact.counted_as_revenue, revenueDeltaTnd: impact.revenue_delta_tnd,
      note: "Impact computed by the Financial Analyst on its SIMULATED baseline dataset.",
    },
  };
}

const ORDER_SELECT = `SELECT o.id, o.user_id, o.course_id, o.workflow_id, o.amount_tnd, o.list_price_tnd, o.payment_method,
       o.payment_scenario, o.status, o.final_status, o.next_step, o.created_at, o.updated_at,
       c.title AS course_title, u.name AS user_name, u.email AS user_email
  FROM orders o JOIN courses c ON c.id = o.course_id JOIN users u ON u.id = o.user_id`;

export const orderView = (r) => ({
  id: r.id,
  workflowId: r.workflow_id,
  courseId: r.course_id,
  courseTitle: r.course_title,
  userId: r.user_id,
  userName: r.user_name,
  userEmail: r.user_email,
  amountTnd: money(r.amount_tnd),
  listPriceTnd: money(r.list_price_tnd),
  paymentMethod: r.payment_method,
  paymentScenario: r.payment_scenario,
  status: r.status,
  finalStatus: r.final_status,
  nextStep: r.next_step,
  createdAt: iso(r.created_at),
  updatedAt: iso(r.updated_at),
});

export async function listOrders(pool, { userId } = {}) {
  const { rows } = userId
    ? await pool.query(`${ORDER_SELECT} WHERE o.user_id = $1 ORDER BY o.created_at DESC`, [userId])
    : await pool.query(`${ORDER_SELECT} ORDER BY o.created_at DESC LIMIT 200`);
  return rows.map(orderView);
}

export async function orderDetail(pool, orderId, { userId } = {}) {
  const params = userId ? [orderId, userId] : [orderId];
  const { rows } = await pool.query(`${ORDER_SELECT} WHERE o.id = $1${userId ? " AND o.user_id = $2" : ""}`, params);
  if (!rows.length) return null;
  const [tx, alerts, events, raw] = await Promise.all([
    pool.query("SELECT id, amount_tnd, status, payment_confirmed, failure_reason, created_at FROM transactions WHERE order_id = $1", [orderId]),
    pool.query("SELECT id, action, risk_score, flags, explanation, status, reviewed_at, created_at FROM fraud_alerts WHERE order_id = $1", [orderId]),
    pool.query("SELECT step, name, agent, status, decision, summary, mode, duration_ms FROM agent_events WHERE order_id = $1 ORDER BY step", [orderId]),
    pool.query("SELECT workflow_result FROM orders WHERE id = $1", [orderId]),
  ]);
  return {
    order: orderView(rows[0]),
    transaction: tx.rows[0] ? { ...tx.rows[0], amount_tnd: money(tx.rows[0].amount_tnd), created_at: iso(tx.rows[0].created_at) } : null,
    fraudAlert: alerts.rows[0] ? { ...alerts.rows[0], created_at: iso(alerts.rows[0].created_at), reviewed_at: iso(alerts.rows[0].reviewed_at) } : null,
    trace: events.rows,
    agents: raw.rows[0]?.workflow_result ? summarizeWorkflow(raw.rows[0].workflow_result) : null,
  };
}
