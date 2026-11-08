import { Link } from "react-router-dom";
import { Bot, Brain, CheckCircle2, ChartNoAxesCombined, CreditCard, LogOut, PackagePlus, ShieldCheck, XCircle, MinusCircle, AlertTriangle } from "lucide-react";

import { STATUS_LABELS } from "../api/client";
import { useAuth } from "../context/AuthContext";
import "../styles/mvp.css";

export function AppShell({ tabs, active, onTab, children, subtitle }) {
  const { user, logout } = useAuth();
  return (
    <div className="q-root">
      <div className="q-shell">
        <aside className="q-side">
          <Link to="/" className="q-logo" style={{ textDecoration: "none" }}><img src="/mascot.webp" alt="" />9antra</Link>
          {tabs.map((t) => (
            <button key={t.id} type="button" className={`tab ${active === t.id ? "active" : ""}`} onClick={() => onTab(t.id)}>
              <t.icon size={18} /> {t.label}
            </button>
          ))}
          <div className="who">
            <div style={{ fontWeight: 700 }}>{user?.name ?? "…"}</div>
            <div className="q-muted" style={{ fontSize: 12 }}>{user?.email}</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
              <span className="q-pill">{subtitle}</span>
              <button type="button" className="q-btn ghost small" onClick={logout} aria-label="Se déconnecter"><LogOut size={14} /></button>
            </div>
          </div>
        </aside>
        <main className="q-main">{children}</main>
      </div>
    </div>
  );
}

export function StatusPill({ status }) {
  const s = STATUS_LABELS[status] ?? { label: status, tone: "" };
  return <span className={`q-pill ${s.tone}`}>{s.label}</span>;
}

const STEP_ICONS = {
  "Sales conversation": Bot,
  "Customer insights": Brain,
  "Order creation": PackagePlus,
  "Fraud screening": ShieldCheck,
  "Payment validation": CreditCard,
  "Financial update": ChartNoAxesCombined,
};

/** Execution trace returned by the AI workflow (or stored in agent_events). */
export function AgentPipeline({ trace }) {
  if (!trace?.length) return null;
  return (
    <div className="q-pipeline">
      {trace.map((t) => {
        const Icon = STEP_ICONS[t.name] ?? Bot;
        const State = t.status === "ok" ? CheckCircle2 : t.status === "skipped" ? MinusCircle : t.status === "stopped" ? AlertTriangle : XCircle;
        return (
          <div key={`${t.step}-${t.name}`} className={`q-step ${t.status}`}>
            <div className="dot"><Icon size={17} /></div>
            <div>
              <div style={{ fontWeight: 700 }}>{t.step}. {t.name} {t.agent && <span className="q-muted" style={{ fontWeight: 400, fontSize: 12 }}>· {t.agent}</span>}</div>
              <div className="q-muted" style={{ fontSize: 13 }}>{t.summary}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <State size={18} />
              {t.decision && <div style={{ fontSize: 12, marginTop: 4 }}>{t.decision}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function AgentSummary({ agents }) {
  if (!agents) return null;
  const { customerIntelligence: ci, fraud, payment, financial } = agents;
  return (
    <div className="q-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
      {ci && <div className="q-card" style={{ padding: 14 }}><div className="q-muted" style={{ fontSize: 12 }}>Customer Intelligence</div>
        <div style={{ fontWeight: 700 }}>{ci.sentiment} · intérêt {ci.interestScore}/100</div><div className="q-muted" style={{ fontSize: 12 }}>{ci.purchaseStage}</div></div>}
      {fraud && <div className="q-card" style={{ padding: 14 }}><div className="q-muted" style={{ fontSize: 12 }}>Fraud Agent</div>
        <div style={{ fontWeight: 700 }}>{fraud.action} · risque {fraud.riskScore}</div><div className="q-muted" style={{ fontSize: 12 }}>{fraud.flags?.join(", ") || "aucune alerte"}</div></div>}
      <div className="q-card" style={{ padding: 14 }}><div className="q-muted" style={{ fontSize: 12 }}>Payment Agent</div>
        <div style={{ fontWeight: 700 }}>{payment ? `${payment.finalStatus} · ${payment.confirmed ? "confirmé" : "non confirmé"}` : "non exécuté"}</div></div>
      {financial && <div className="q-card" style={{ padding: 14 }}><div className="q-muted" style={{ fontSize: 12 }}>Financial Analyst</div>
        <div style={{ fontWeight: 700 }}>{financial.countedAsRevenue ? `+${financial.revenueDeltaTnd} TND de revenu` : "aucun revenu compté"}</div></div>}
    </div>
  );
}
