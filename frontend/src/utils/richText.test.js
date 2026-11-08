import { test } from "node:test";
import assert from "node:assert/strict";

import { parseInline, parseRichText, stripAgentPrefix } from "./richText.js";

test("strips the technical agent prefix", () => {
  assert.equal(stripAgentPrefix("[MOCK] Bonjour"), "Bonjour");
  assert.equal(stripAgentPrefix("[FALLBACK] Salut"), "Salut");
  assert.equal(stripAgentPrefix("Texte [MOCK] normal"), "Texte [MOCK] normal");
});

test("parses bold segments", () => {
  assert.deepEqual(parseInline("a **b** c"), [{ text: "a " }, { text: "b", bold: true }, { text: " c" }]);
  assert.deepEqual(parseInline("rien"), [{ text: "rien" }]);
});

test("splits paragraphs, bullets and bullet details", () => {
  const blocks = parseRichText(
    "[MOCK] Voici :\n\nIntro :\n• **Python for AI** — 199 TND\n  Les bases de Python.\n• Autre\n\n👉 Question ?",
  );
  assert.deepEqual(blocks, [
    { type: "p", text: "Voici :" },
    { type: "p", text: "Intro :" },
    { type: "ul", items: [
      { text: "**Python for AI** — 199 TND", detail: "Les bases de Python." },
      { text: "Autre", detail: "" },
    ] },
    { type: "p", text: "👉 Question ?" },
  ]);
});

test("empty input gives no blocks", () => {
  assert.deepEqual(parseRichText(""), []);
  assert.deepEqual(parseRichText(null), []);
});
