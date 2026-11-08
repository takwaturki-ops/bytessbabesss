import { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, MessageSquare, Plus, Receipt, Send, ShieldCheck } from "lucide-react";

import { createConversation, getCourses, getMessages, getPurchase, listConversations, listPurchases, sendMessage } from "../api/client";
import { getErrorMessage } from "../api/authHelpers";
import PurchaseModal from "../components/PurchaseModal";
import RichText from "../components/RichText";
import SecurityPanel from "../components/SecurityPanel";
import { AgentPipeline, AgentSummary, AppShell, StatusPill } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { stripAgentPrefix } from "../utils/richText";

const TABS = [
  { id: "chat", label: "Assistant IA", icon: MessageSquare },
  { id: "courses", label: "Catalogue", icon: BookOpen },
  { id: "purchases", label: "Mes achats", icon: Receipt },
  { id: "security", label: "Sécurité", icon: ShieldCheck },
];

const MODE_LABEL = { live: "IA Claude", mock: "réponses modèles", fallback: "IA indisponible · réponse modèle" };

const fmt = (d) => (d ? new Date(d).toLocaleString("fr-TN", { dateStyle: "short", timeStyle: "short" }) : "");

function Chat({ onBuy }) {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  const refreshList = useCallback(() => listConversations().then(setConversations).catch((e) => setError(getErrorMessage(e))), []);
  useEffect(() => { refreshList(); }, [refreshList]);
  useEffect(() => {
    if (!activeId) { setMessages([]); return; }
    getMessages(activeId).then((d) => setMessages(d.messages)).catch((e) => setError(getErrorMessage(e)));
  }, [activeId]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, sending]);

  const newConversation = async () => {
    const c = await createConversation();
    await refreshList();
    setActiveId(c.id);
  };

  const send = async (e) => {
    e.preventDefault();
    const content = text.trim();
    if (!content || sending) return;
    setError("");
    setSending(true);
    let id = activeId;
    try {
      if (!id) {
        id = (await createConversation()).id;
        setActiveId(id);
      }
      setMessages((m) => [...m, { id: `tmp-${Date.now()}`, role: "user", content }]);
      setText("");
      await sendMessage(id, content);
      const d = await getMessages(id);
      setMessages(d.messages);
      refreshList();
    } catch (err) {
      setError(getErrorMessage(err, "Message non envoyé."));
      if (id) getMessages(id).then((d) => setMessages(d.messages)).catch(() => {});
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="q-chat">
      <div className="q-conv-list">
        <button type="button" className="q-btn small" onClick={newConversation}><Plus size={14} /> Nouvelle conversation</button>
        {conversations.map((c) => (
          <button key={c.id} type="button" className={`q-conv ${c.id === activeId ? "active" : ""}`} onClick={() => setActiveId(c.id)}>
            <strong>{c.title}</strong><small>{c.lastMessage ? stripAgentPrefix(c.lastMessage) : "Pas encore de message"}</small><small>{fmt(c.updatedAt)}</small>
          </button>
        ))}
        {!conversations.length && <p className="q-muted" style={{ fontSize: 13 }}>Aucune conversation pour l'instant.</p>}
      </div>
      <div className="q-card q-chat-panel">
        <div className="q-messages">
          {!messages.length && (
            <div style={{ textAlign: "center", margin: "auto" }}>
              <img src="/mascot.webp" alt="" style={{ width: 120, borderRadius: 18 }} />
              <p><strong>Ahla bik !</strong> Pose ta question : « Je veux apprendre le machine learning », « C'est trop cher »…</p>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`q-msg ${m.role}`}>
              {m.role === "assistant" ? <RichText text={m.content} /> : m.content}
              {m.role === "assistant" && m.metadata && (
                <>
                  <div className="meta">
                    <span className="q-pill">Sales Agent</span>
                    <span className="q-pill">intention : {m.metadata.detected_intent}</span>
                    {m.metadata.objection_type && m.metadata.objection_type !== "none" && <span className="q-pill warn">objection : {m.metadata.objection_type}</span>}
                    {m.metadata.mode && <span className={`q-pill ${m.metadata.mode === "live" ? "" : "warn"}`}>{MODE_LABEL[m.metadata.mode] ?? m.metadata.mode}</span>}
                  </div>
                  {m.metadata.recommended_courses?.length > 0 && (
                    <div className="q-reco">
                      {m.metadata.recommended_courses.map((c) => (
                        <div key={c.course_id} className="item">
                          <div><strong>{c.title}</strong><div className="q-muted" style={{ fontSize: 12 }}>{c.level} · {c.duration_weeks} semaines · {c.reason}</div></div>
                          <button type="button" className="q-btn small" onClick={() => onBuy({ id: c.course_id, title: c.title, priceTnd: c.price_tnd }, activeId)}>
                            {c.price_tnd} TND · Acheter
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          {sending && <div className="q-typing">Les agents 9antra réfléchissent…</div>}
          <div ref={endRef} />
        </div>
        {error && <div className="q-error">{error}</div>}
        <form className="q-composer" onSubmit={send}>
          <input className="q-input" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000}
            placeholder="Écris ton message (français, anglais ou derja)…" aria-label="Message" />
          <button type="submit" className="q-btn" disabled={sending || !text.trim()} aria-label="Envoyer"><Send size={16} /></button>
        </form>
      </div>
    </div>
  );
}

function Courses({ onBuy }) {
  const [courses, setCourses] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { getCourses().then(setCourses).catch((e) => setError(getErrorMessage(e))); }, []);
  if (error) return <div className="q-error">{error}</div>;
  if (!courses) return <p className="q-muted">Chargement du catalogue…</p>;
  return (
    <div className="q-grid">
      {courses.map((c) => (
        <div key={c.id} className="q-card q-course">
          <span className="q-pill">{c.level}</span> <span className="q-pill">{c.category}</span>
          <h3>{c.title}</h3>
          <p className="q-muted" style={{ fontSize: 14, minHeight: 42 }}>{c.description}</p>
          <div className="q-muted" style={{ fontSize: 13 }}>{c.durationHours} h · {c.durationWeeks} semaines</div>
          <div className="row"><span className="price">{c.priceTnd} TND</span>
            <button type="button" className="q-btn small" onClick={() => onBuy(c)}>Acheter</button></div>
        </div>
      ))}
    </div>
  );
}

function Purchases({ refreshKey }) {
  const [orders, setOrders] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { listPurchases().then(setOrders).catch((e) => setError(getErrorMessage(e))); }, [refreshKey]);
  if (error) return <div className="q-error">{error}</div>;
  if (!orders) return <p className="q-muted">Chargement…</p>;
  if (!orders.length) return <p className="q-muted">Aucun achat pour l'instant. Parcours le catalogue ou demande conseil à l'assistant.</p>;
  return (
    <div className="q-two">
      <div className="q-card q-scroll">
        <table className="q-table">
          <thead><tr><th>Commande</th><th>Cours</th><th>Montant</th><th>Statut</th><th>Date</th></tr></thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="click" onClick={() => getPurchase(o.id).then(setDetail).catch((e) => setError(getErrorMessage(e)))}>
                <td>{o.id}</td><td>{o.courseTitle}</td><td>{o.amountTnd} TND</td><td><StatusPill status={o.status} /></td><td>{fmt(o.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="q-card">
        {!detail ? <p className="q-muted">Sélectionne une commande pour voir le détail du traitement par les agents.</p> : (
          <>
            <h3 style={{ marginTop: 0 }}>{detail.order.courseTitle}</h3>
            <p><StatusPill status={detail.order.status} /> <span className="q-muted">{detail.order.finalStatus} · {detail.order.amountTnd} TND</span></p>
            <p className="q-muted" style={{ fontSize: 13 }}>Transaction : {detail.transaction ? `${detail.transaction.id} (${detail.transaction.status})` : "aucune (paiement non traité)"}</p>
            {detail.fraudAlert && <p className="q-muted" style={{ fontSize: 13 }}>Alerte sécurité : {detail.fraudAlert.action} · {detail.fraudAlert.status}</p>}
            <AgentPipeline trace={detail.trace} />
            <AgentSummary agents={detail.agents} />
          </>
        )}
      </div>
    </div>
  );
}

export default function UserApp() {
  const { user } = useAuth();
  const [tab, setTab] = useState("chat");
  const [buying, setBuying] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const titles = { chat: "Assistant IA 9antra", courses: "Catalogue des formations", purchases: "Historique des achats", security: "Sécurité du compte" };

  return (
    <AppShell tabs={TABS} active={tab} onTab={setTab} subtitle="Apprenant">
      <div className="q-head">
        <div><h1>{titles[tab]}</h1><div className="q-muted">Bienvenue {user?.name?.split(" ")[0] ?? ""} 👋</div></div>
      </div>
      {tab === "chat" && <Chat onBuy={(course, conversationId) => setBuying({ course, conversationId })} />}
      {tab === "courses" && <Courses onBuy={(course) => setBuying({ course })} />}
      {tab === "purchases" && <Purchases refreshKey={refreshKey} />}
      {tab === "security" && <SecurityPanel />}
      {buying && (
        <PurchaseModal course={buying.course} conversationId={buying.conversationId}
          onClose={() => setBuying(null)} onDone={() => setRefreshKey((k) => k + 1)} />
      )}
    </AppShell>
  );
}
