// Light markup used by the AI agents: blank-line paragraphs, "• " / "- " bullets
// (an indented next line is the bullet's detail) and **bold**. No HTML is ever interpreted.

const AGENT_PREFIX = /^\[(MOCK|FALLBACK)\]\s*/;
const BULLET = /^\s*(?:•|-|\*)\s+/;

/** Removes the technical "[MOCK] " / "[FALLBACK] " label (the mode is shown as a badge instead). */
export function stripAgentPrefix(text) {
  return String(text ?? "").replace(AGENT_PREFIX, "");
}

/** "a **b** c" -> [{text:"a "}, {text:"b", bold:true}, {text:" c"}] */
export function parseInline(text) {
  const parts = [];
  const re = /\*\*(.+?)\*\*/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) });
    parts.push({ text: m[1], bold: true });
    last = re.lastIndex;
  }
  if (last < text.length) parts.push({ text: text.slice(last) });
  return parts;
}

/** Text -> blocks: {type:"p", text} | {type:"ul", items:[{text, detail}]} */
export function parseRichText(raw) {
  const blocks = [];
  const text = stripAgentPrefix(raw).replace(/\r\n/g, "\n").trim();
  if (!text) return blocks;
  for (const para of text.split(/\n{2,}/)) {
    let list = null;
    let lines = [];
    const flushLines = () => {
      if (lines.length) blocks.push({ type: "p", text: lines.join("\n") });
      lines = [];
    };
    for (const line of para.split("\n")) {
      if (BULLET.test(line)) {
        flushLines();
        if (!list) {
          list = { type: "ul", items: [] };
          blocks.push(list);
        }
        list.items.push({ text: line.replace(BULLET, ""), detail: "" });
      } else if (list && /^\s{2,}\S/.test(line)) {
        const item = list.items[list.items.length - 1];
        item.detail = item.detail ? `${item.detail} ${line.trim()}` : line.trim();
      } else {
        list = null;
        lines.push(line);
      }
    }
    flushLines();
  }
  return blocks;
}
