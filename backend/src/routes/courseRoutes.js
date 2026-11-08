import express from "express";

import { asyncHandler, fail, iso, money, ok } from "../utils/http.js";

export const courseView = (row) => ({
  id: row.id,
  title: row.title,
  titleAr: row.title_ar,
  category: row.category,
  level: row.level,
  priceTnd: money(row.price_tnd),
  durationHours: row.duration_hours,
  durationWeeks: row.duration_weeks,
  description: row.description,
  isActive: row.is_active,
  createdAt: iso(row.created_at),
});

const COLUMNS = "id, title, title_ar, category, level, price_tnd, duration_hours, duration_weeks, description, is_active, created_at";

export function createCourseRouter({ pool }) {
  const router = express.Router();

  router.get("/", asyncHandler(async (req, res) => {
    const { rows } = await pool.query(`SELECT ${COLUMNS} FROM courses WHERE is_active = TRUE ORDER BY price_tnd ASC, id ASC`);
    return ok(res, rows.map(courseView));
  }));

  router.get("/:id", asyncHandler(async (req, res) => {
    const { rows } = await pool.query(`SELECT ${COLUMNS} FROM courses WHERE id = $1 AND is_active = TRUE`, [req.params.id]);
    if (!rows.length) return fail(res, 404, "Course not found");
    return ok(res, courseView(rows[0]));
  }));

  return router;
}
