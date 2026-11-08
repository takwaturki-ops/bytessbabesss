import { parseInline, parseRichText } from "../utils/richText";

function Inline({ text }) {
  return parseInline(text).map((part, i) => (part.bold ? <strong key={i}>{part.text}</strong> : <span key={i}>{part.text}</span>));
}

/** Renders agent replies (paragraphs, bullets, **bold**) as React elements: no raw HTML. */
export default function RichText({ text }) {
  return (
    <div className="q-rich">
      {parseRichText(text).map((block, i) =>
        block.type === "ul" ? (
          <ul key={i}>
            {block.items.map((item, j) => (
              <li key={j}>
                <Inline text={item.text} />
                {item.detail && <div className="detail"><Inline text={item.detail} /></div>}
              </li>
            ))}
          </ul>
        ) : (
          <p key={i}><Inline text={block.text} /></p>
        ),
      )}
    </div>
  );
}
