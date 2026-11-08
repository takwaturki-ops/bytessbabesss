import express from "express";

import { AiServiceError } from "../services/aiClient.js";
import {
  PAYMENT_METHODS, PAYMENT_SCENARIOS, buildWorkflowRequest, listOrders, orderDetail, persistWorkflowResult,
  summarizeWorkflow,
} from "../services/purchaseService.js";
import { asyncHandler, fail, ok } from "../utils/http.js";
import { findOwnedConversation } from "./conversationRoutes.js";

export function createPurchaseRouter({ pool, ai }) {
  const router = express.Router();
  const inFlight = new Set(); // one purchase at a time per user + course (double-click protection)

  router.get("/", asyncHandler(async (req, res) => ok(res, await listOrders(pool, { userId: req.auth.userId }))));

  router.get("/:id", asyncHandler(async (req, res) => {
    const detail = await orderDetail(pool, req.params.id, { userId: req.auth.userId });
    if (!detail) return fail(res, 404, "Order not found");
    return ok(res, detail);
  }));

  // Simulated purchase: Sales -> Customer Intelligence -> Order -> Fraud -> Payment -> Financial (AI workflow).
  router.post("/", asyncHandler(async (req, res) => {
    const { course_id: courseId, conversation_id: conversationId, message, discount_code: discountCode } = req.body || {};
    const paymentScenario = req.body?.payment_scenario ?? "success";
    const paymentMethod = req.body?.payment_method ?? "card";
    const errors = [];
    if (typeof courseId !== "string" || !/^[A-Za-z0-9_-]{1,20}$/.test(courseId)) errors.push("course_id is required");
    if (!PAYMENT_SCENARIOS.includes(paymentScenario)) errors.push(`payment_scenario must be one of: ${PAYMENT_SCENARIOS.join(", ")}`);
    if (!PAYMENT_METHODS.includes(paymentMethod)) errors.push(`payment_method must be one of: ${PAYMENT_METHODS.join(", ")}`);
    if (message !== undefined && (typeof message !== "string" || message.length > 2000)) errors.push("message must be a string of at most 2000 characters");
    if (discountCode !== undefined && (typeof discountCode !== "string" || discountCode.length > 32)) errors.push("discount_code is invalid");
    if (errors.length) return fail(res, 422, ...errors);

    const userId = req.auth.userId;
    const { rows: courseRows } = await pool.query("SELECT * FROM courses WHERE id = $1 AND is_active = TRUE", [courseId]);
    const course = courseRows[0];
    if (!course) return fail(res, 404, "Course not found");

    let ownedConversationId = null;
    if (conversationId !== undefined && conversationId !== null) {
      const conv = await findOwnedConversation(pool, conversationId, userId);
      if (!conv) return fail(res, 404, "Conversation not found");
      ownedConversationId = conv.id;
    }

    const paid = await pool.query("SELECT id FROM orders WHERE user_id = $1 AND course_id = $2 AND status = 'paid' LIMIT 1", [userId, courseId]);
    if (paid.rows.length) return fail(res, 409, `You already own this course (order ${paid.rows[0].id})`);

    const lockKey = `${userId}:${courseId}`;
    if (inFlight.has(lockKey)) return fail(res, 409, "A purchase for this course is already in progress");
    inFlight.add(lockKey);
    try {
      const request = await buildWorkflowRequest(pool, {
        userId, course, conversationId: ownedConversationId, message, paymentScenario, paymentMethod, discountCode,
      });
      let response;
      try {
        response = await ai.purchase(request);
      } catch (err) {
        if (err instanceof AiServiceError) {
          // Fail closed: no fraud screening possible -> no order, no payment.
          return fail(res, 503, "AI service unavailable: purchase not processed (no order created, no payment)");
        }
        throw err;
      }
      const result = response.body;
      if (response.status === 404 && result?.final_status === "unknown_course") return fail(res, 404, "Course unknown to the AI catalog");
      if (response.status === 422) return fail(res, 502, "AI workflow rejected the request", JSON.stringify(result?.detail ?? result).slice(0, 300));
      if (response.status !== 200 || !result?.final_status) return fail(res, 502, "AI workflow failed", ...(result?.errors ?? []));

      const orderId = await persistWorkflowResult(pool, { userId, course, conversationId: ownedConversationId, request, result });
      return ok(res, {
        workflowId: result.workflow_id,
        orderId,
        transactionId: result.payment_agent_result ? result.transaction_id : null,
        finalStatus: result.final_status,
        purchaseConfirmed: result.purchase_confirmed === true,
        nextStep: result.next_step,
        course: { id: course.id, title: course.title },
        amountTnd: result.amount_tnd,
        agents: summarizeWorkflow(result),
        trace: result.execution_trace,
        warnings: result.warnings,
        llmMode: result.llm_mode,
        dataNotice: result.data_notice,
      }, orderId ? 201 : 200);
    } finally {
      inFlight.delete(lockKey);
    }
  }));

  return router;
}
