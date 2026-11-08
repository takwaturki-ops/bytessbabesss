import express from "express";

import { AiServiceError } from "../services/aiClient.js";
import { asyncHandler, fail, iso, ok } from "../utils/http.js";

const MAX_MESSAGE = 2000;   // SalesInput.customer_message max_length
const MAX_TURN = 4000;      // Turn.text max_length
const HISTORY_TURNS = 20;   // SalesInput.conversation_history max_length is 50

export const customerIdFor = (userId) => `USER-${userId}`;

const messageView = (row) => ({
  id: row.id,
  role: row.role,
  content: row.content,
  metadata: row.metadata ?? null,
  createdAt: iso(row.created_at),
});

const conversationView = (row) => ({
  id: row.id,
  title: row.title,
  createdAt: iso(row.created_at),
  updatedAt: iso(row.updated_at),
  lastMessage: row.last_message ?? null,
});

/** DB messages -> AI Turn[] ({role: customer|agent, text}). */
export async function loadTurns(pool, conversationId, limit = HISTORY_TURNS) {
  const { rows } = await pool.query(
    "SELECT role, content FROM messages WHERE conversation_id = $1 ORDER BY id DESC LIMIT $2",
    [conversationId, limit],
  );
  return rows.reverse().map((m) => ({
    role: m.role === "user" ? "customer" : "agent",
    text: m.content.slice(0, MAX_TURN),
  }));
}

export async function findOwnedConversation(pool, conversationId, userId) {
  const id = Number(conversationId);
  if (!Number.isInteger(id) || id <= 0) return null;
  const { rows } = await pool.query("SELECT * FROM conversations WHERE id = $1 AND user_id = $2", [id, userId]);
  return rows[0] ?? null;
}

export function createConversationRouter({ pool, ai }) {
  const router = express.Router();

  router.get("/", asyncHandler(async (req, res) => {
    const [convs, msgs] = await Promise.all([
      pool.query(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = $1 ORDER BY updated_at DESC, id DESC",
        [req.auth.userId],
      ),
      pool.query(
        `SELECT m.conversation_id, m.content FROM messages m JOIN conversations c ON c.id = m.conversation_id
          WHERE c.user_id = $1 ORDER BY m.id ASC`,
        [req.auth.userId],
      ),
    ]);
    const last = {};
    for (const m of msgs.rows) last[m.conversation_id] = m.content;
    return ok(res, convs.rows.map((c) => conversationView({ ...c, last_message: last[c.id] ?? null })));
  }));

  router.post("/", asyncHandler(async (req, res) => {
    const title = typeof req.body?.title === "string" && req.body.title.trim()
      ? req.body.title.trim().slice(0, 200) : "Nouvelle conversation";
    const { rows } = await pool.query(
      "INSERT INTO conversations (user_id, title) VALUES ($1, $2) RETURNING id, title, created_at, updated_at",
      [req.auth.userId, title],
    );
    return ok(res, conversationView(rows[0]), 201);
  }));

  router.get("/:id/messages", asyncHandler(async (req, res) => {
    const conversation = await findOwnedConversation(pool, req.params.id, req.auth.userId);
    if (!conversation) return fail(res, 404, "Conversation not found");
    const { rows } = await pool.query(
      "SELECT id, role, content, metadata, created_at FROM messages WHERE conversation_id = $1 ORDER BY id ASC",
      [conversation.id],
    );
    return ok(res, { conversation: conversationView(conversation), messages: rows.map(messageView) });
  }));

  // Send a message: persisted, answered by the Sales Agent (POST /agents/sales), answer persisted.
  router.post("/:id/messages", asyncHandler(async (req, res) => {
    const content = typeof req.body?.content === "string" ? req.body.content.trim() : "";
    if (!content) return fail(res, 422, "Message content is required");
    if (content.length > MAX_MESSAGE) return fail(res, 422, `Message must be at most ${MAX_MESSAGE} characters`);

    const conversation = await findOwnedConversation(pool, req.params.id, req.auth.userId);
    if (!conversation) return fail(res, 404, "Conversation not found");

    const history = await loadTurns(pool, conversation.id);
    const userMsg = await pool.query(
      "INSERT INTO messages (conversation_id, role, content) VALUES ($1, 'user', $2) RETURNING id, role, content, metadata, created_at",
      [conversation.id, content],
    );
    if (!history.length && conversation.title === "Nouvelle conversation") {
      await pool.query("UPDATE conversations SET title = $1 WHERE id = $2", [content.slice(0, 60), conversation.id]);
    }

    let result;
    try {
      result = await ai.sales({
        customer_message: content,
        conversation_history: history,
        customer_id: customerIdFor(req.auth.userId),
        channel: "chat",
      });
    } catch (err) {
      if (err instanceof AiServiceError) {
        return fail(res, 503, "AI service unavailable: your message was saved, please retry later");
      }
      throw err;
    }
    if (result.status !== 200 || result.body?.status !== "ok") {
      return fail(res, 502, "AI service returned an error", ...(result.body?.errors ?? []));
    }

    const data = result.body.data;
    const metadata = {
      agent: "sales_agent",
      detected_intent: data.detected_intent,
      objection_type: data.objection_type,
      next_action: data.next_action,
      recommended_courses: data.recommended_courses,
      purchase_intent_score: data.purchase_intent_score,
      catalog_grounded: data.catalog_grounded,
      mode: result.body.meta?.mode,
    };
    const assistantMsg = await pool.query(
      "INSERT INTO messages (conversation_id, role, content, metadata) VALUES ($1, 'assistant', $2, $3) " +
        "RETURNING id, role, content, metadata, created_at",
      [conversation.id, data.reply, JSON.stringify(metadata)],
    );
    await pool.query("UPDATE conversations SET updated_at = NOW() WHERE id = $1", [conversation.id]);
    return ok(res, { userMessage: messageView(userMsg.rows[0]), assistantMessage: messageView(assistantMsg.rows[0]) }, 201);
  }));

  return router;
}
