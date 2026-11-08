import { useCallback, useEffect, useState } from "react";
import { Activity, BookOpen, LayoutDashboard, RefreshCw, ShieldAlert, ShoppingCart, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { admin } from "../api/client";
import { getErrorMessage } from "../api/authHelpers";
import { AgentPipeline, AgentSummary, AppShell, StatusPill } from "../components/ui";

const TABS = [
  { id: "overview", label: "Vue d'ensemble", icon: LayoutDashboard },
  { id: "orders", label: "Commandes", icon: ShoppingCart },
  { id: "alerts", label: "Alertes fraude", icon: ShieldAlert },
  { id: "users", label: "Utilisateurs", icon: Users },
  { id: "courses", label: "Cours", icon: BookOpen },
  { id: "activity", label: "Activité agents", icon: Activity },
];
const COLORS = ["#3ee8ff", "#8b5cf6", "#e879f9", "#34d399", "#fbbf24", "#f87171", "#60a5fa", "#a78bfa"];
const fmt = (d) => (d ? new Date(d).toLocaleString("fr-TN", { dateStyle: "short", timeStyle: "short" }) : "");
const tooltipStyle = { background: "#141840", border: "1px solid rgba(120,140,255,.3)", borderRadius: 12, color: "#eef0ff" };

function useLoad(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: "" });
  const reload = useCallback(() => {
    setState((s) => ({ ...s, error: "" }));
    fn().then((data) => setState({ data, error: "" })).catch((e) => setState({ data: null, error: getErrorMessage(e) }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { reload(); }, [reload]);
  return { ...state, reload };
}

function Overview() {
  const stats = useLoad(admin.stats);
  const insights = useLoad(admin.insights);
  if (stats.error) return <div className="q-error">{stats.error}</div>;
  const s = stats.data;
  if (!s) return <p className="q-muted">Chargement…</p>;
  const byStatus = Object.entries(s.orders.byStatus).map(([name, value]) => ({ name, value }));
  return (
    <>
      <div className="q-stats">
        <div className="q-card q-stat"><div className="q-muted">Revenu confirmé</div><div className="v q-gradient-text">{s.revenue.totalTnd} TND</div><div className="q-muted" style={{ fontSize: 12 }}>{s.revenue.paidOrders} commandes payées</div></div>
        <div className="q-card q-stat"><div className="q-muted">Commandes</div><div className="v">{s.orders.total}</div><div className="q-muted" style={{ fontSize: 12 }}>conversion {(s.revenue.conversionRate * 100).toFixed(1)} %</div></div>
        <div className="q-card q-stat"><div className="q-muted">Alertes fraude ouvertes</div><div className="v" style={{ color: s.fraudAlerts.open ? "var(--warn)" : undefined }}>{s.fraudAlerts.open}</div><div className="q-muted" style={{ fontSize: 12 }}>{s.fraudAlerts.total} au total</div></div>
        <div className="q-card q-stat"><div className="q-muted">Utilisateurs</div><div className="v">{s.users.total}</div><div className="q-muted" style={{ fontSize: 12 }}>{s.users.byRole.admin ?? 0} admin · {s.users.byRole.customer ?? 0} apprenants</div></div>
      </div>
      <div className="q-two">
        <div className="q-card">
          <h3 style={{ marginTop: 0 }}>Revenu par cours (TND)</h3>
          {s.revenue.byCourse.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={s.revenue.byCourse}><CartesianGrid stroke="rgba(120,140,255,.1)" /><XAxis dataKey="courseId" stroke="#9aa3d6" /><YAxis stroke="#9aa3d6" />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${v} TND`} labelFormatter={(id) => s.revenue.byCourse.find((c) => c.courseId === id)?.title ?? id} />
                <Bar dataKey="revenueTnd" radius={[8, 8, 0, 0]}>{s.revenue.byCourse.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="q-muted">Aucun paiement confirmé pour l'instant.</p>}
        </div>
        <div className="q-card">
          <h3 style={{ marginTop: 0 }}>Commandes par statut</h3>
          {byStatus.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={byStatus} layout="vertical"><CartesianGrid stroke="rgba(120,140,255,.1)" /><XAxis type="number" allowDecimals={false} stroke="#9aa3d6" /><YAxis type="category" dataKey="name" width={150} stroke="#9aa3d6" />
                <Tooltip contentStyle={tooltipStyle} /><Bar dataKey="value" radius={[0, 8, 8, 0]}>{byStatus.map((_, i) => <Cell key={i} fill={COLORS[(i + 2) % COLORS.length]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="q-muted">Aucune commande.</p>}
        </div>
      </div>
      <div className="q-card" style={{ marginTop: 18 }}>
        <div className="q-head" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Analyse du Financial Analyst Agent</h3>
          <button type="button" className="q-btn ghost small" onClick={insights.reload}><RefreshCw size={14} /> Actualiser</button></div>
        {insights.error && <div className="q-error">{insights.error}</div>}
        {!insights.data && !insights.error && <p className="q-muted">L'agent analyse les commandes…</p>}
        {insights.data && (
          <>
            <p>{insights.data.narrative}</p>
            <ul>{insights.data.insights.map((i) => <li key={i} className="q-muted">{i}</li>)}</ul>
            <p className="q-notice">Calculs pandas sur les commandes de la base · mode {insights.data.meta?.mode} · taux de succès paiement {(insights.data.metrics.payment_success_rate * 100).toFixed(1)} %</p>
          </>
        )}
      </div>
      <p className="q-notice">{s.dataNotice}</p>
    </>
  );
}

function Orders() {
  const orders = useLoad(admin.orders);
  const [detail, setDetail] = useState(null);
  if (orders.error) return <div className="q-error">{orders.error}</div>;
  if (!orders.data) return <p className="q-muted">Chargement…</p>;
  return (
    <div className="q-two">
      <div className="q-card q-scroll">
        <table className="q-table">
          <thead><tr><th>Commande</th><th>Client</th><th>Cours</th><th>Montant</th><th>Statut</th><th>Scénario</th></tr></thead>
          <tbody>{orders.data.map((o) => (
            <tr key={o.id} className="click" onClick={() => admin.order(o.id).then(setDetail)}>
              <td>{o.id}<div className="q-muted" style={{ fontSize: 11 }}>{fmt(o.createdAt)}</div></td><td>{o.userName}<div className="q-muted" style={{ fontSize: 11 }}>{o.userEmail}</div></td>
              <td>{o.courseTitle}</td><td>{o.amountTnd} TND</td><td><StatusPill status={o.status} /></td><td className="q-muted">{o.paymentScenario}</td>
            </tr>))}
          </tbody>
        </table>
        {!orders.data.length && <p className="q-muted">Aucune commande.</p>}
      </div>
      <div className="q-card">
        {!detail ? <p className="q-muted">Sélectionne une commande.</p> : (
          <>
            <h3 style={{ marginTop: 0 }}>{detail.order.id} · {detail.order.courseTitle}</h3>
            <p><StatusPill status={detail.order.status} /> <span className="q-muted">{detail.order.finalStatus}</span></p>
            <p className="q-muted" style={{ fontSize: 13 }}>Transaction : {detail.transaction ? `${detail.transaction.id} · ${detail.transaction.status} · confirmé ${detail.transaction.payment_confirmed ? "oui" : "non"}` : "aucune"}</p>
            <AgentPipeline trace={detail.trace} />
            <AgentSummary agents={detail.agents} />
          </>
        )}
      </div>
    </div>
  );
}

function Alerts() {
  const alerts = useLoad(admin.alerts);
  const [error, setError] = useState("");
  const decide = async (id, decision) => {
    setError("");
    try { await admin.decide(id, decision); alerts.reload(); } catch (e) { setError(getErrorMessage(e)); }
  };
  if (alerts.error) return <div className="q-error">{alerts.error}</div>;
  if (!alerts.data) return <p className="q-muted">Chargement…</p>;
  return (
    <div className="q-card q-scroll">
      {error && <div className="q-error">{error}</div>}
      <table className="q-table">
        <thead><tr><th>Date</th><th>Client</th><th>Commande</th><th>Décision agent</th><th>Règles</th><th>Statut</th><th /></tr></thead>
        <tbody>{alerts.data.map((a) => (
          <tr key={a.id}>
            <td>{fmt(a.createdAt)}</td><td>{a.userName}<div className="q-muted" style={{ fontSize: 11 }}>{a.userEmail}</div></td>
            <td>{a.orderId}<div className="q-muted" style={{ fontSize: 11 }}>{a.courseId} · {a.amountTnd} TND</div></td>
            <td><span className={`q-pill ${a.action === "block" ? "bad" : "warn"}`}>{a.action}</span> <span className="q-muted">risque {a.riskScore}</span></td>
            <td className="q-muted" style={{ fontSize: 12 }}>{a.flags.join(", ")}</td>
            <td><span className={`q-pill ${a.status === "open" ? "warn" : a.status === "approved" ? "ok" : "bad"}`}>{a.status}</span></td>
            <td>{a.status === "open" && (
              <div style={{ display: "flex", gap: 6 }}>
                {a.action !== "block" && <button type="button" className="q-btn small" onClick={() => decide(a.id, "approve")}>Approuver</button>}
                <button type="button" className="q-btn small danger" onClick={() => decide(a.id, "reject")}>Rejeter</button>
              </div>)}
            </td>
          </tr>))}
        </tbody>
      </table>
      {!alerts.data.length && <p className="q-muted">Aucune alerte.</p>}
      <p className="q-notice">Approuver enregistre la décision humaine ; cela ne simule pas de paiement : la commande passe « approuvée, paiement à refaire ».</p>
    </div>
  );
}

function UsersTab() {
  const users = useLoad(admin.users);
  const [error, setError] = useState("");
  const setRole = async (id, role) => {
    setError("");
    try { await admin.setRole(id, role); users.reload(); } catch (e) { setError(getErrorMessage(e)); }
  };
  if (users.error) return <div className="q-error">{users.error}</div>;
  if (!users.data) return <p className="q-muted">Chargement…</p>;
  return (
    <div className="q-card q-scroll">
      {error && <div className="q-error">{error}</div>}
      <table className="q-table">
        <thead><tr><th>Nom</th><th>Email</th><th>Rôle</th><th>Commandes</th><th>Inscrit le</th><th /></tr></thead>
        <tbody>{users.data.map((u) => (
          <tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td><span className={`q-pill ${u.role === "admin" ? "ok" : ""}`}>{u.role}</span></td>
            <td>{u.orderCount}</td><td>{fmt(u.createdAt)}</td>
            <td><button type="button" className="q-btn ghost small" onClick={() => setRole(u.id, u.role === "admin" ? "customer" : "admin")}>
              {u.role === "admin" ? "Retirer admin" : "Promouvoir admin"}</button></td></tr>))}
        </tbody>
      </table>
    </div>
  );
}

function CoursesTab() {
  const courses = useLoad(admin.courses);
  const [error, setError] = useState("");
  const toggle = async (c) => {
    setError("");
    try { await admin.updateCourse(c.id, { is_active: !c.isActive }); courses.reload(); } catch (e) { setError(getErrorMessage(e)); }
  };
  if (courses.error) return <div className="q-error">{courses.error}</div>;
  if (!courses.data) return <p className="q-muted">Chargement…</p>;
  return (
    <div className="q-card q-scroll">
      {error && <div className="q-error">{error}</div>}
      <table className="q-table">
        <thead><tr><th>ID</th><th>Titre</th><th>Niveau</th><th>Prix</th><th>Durée</th><th>Statut</th><th /></tr></thead>
        <tbody>{courses.data.map((c) => (
          <tr key={c.id}><td>{c.id}</td><td>{c.title}<div className="q-muted" style={{ fontSize: 11 }}>{c.titleAr}</div></td><td>{c.level}</td>
            <td>{c.priceTnd} TND</td><td>{c.durationWeeks} sem.</td>
            <td><span className={`q-pill ${c.isActive ? "ok" : "bad"}`}>{c.isActive ? "actif" : "masqué"}</span></td>
            <td><button type="button" className="q-btn ghost small" onClick={() => toggle(c)}>{c.isActive ? "Masquer" : "Publier"}</button></td></tr>))}
        </tbody>
      </table>
      <p className="q-notice">Les prix proviennent du catalogue du service IA utilisé par le workflow d'achat : ils ne sont pas modifiables ici.</p>
    </div>
  );
}

function ActivityTab() {
  const activity = useLoad(admin.activity);
  if (activity.error) return <div className="q-error">{activity.error}</div>;
  if (!activity.data) return <p className="q-muted">Chargement…</p>;
  return (
    <div className="q-card q-scroll">
      <table className="q-table">
        <thead><tr><th>Date</th><th>Commande</th><th>Étape</th><th>Agent</th><th>Statut</th><th>Décision</th><th>Détail</th></tr></thead>
        <tbody>{activity.data.map((e, i) => (
          <tr key={`${e.order_id}-${e.step}-${i}`}><td>{fmt(e.created_at)}</td><td>{e.order_id}</td><td>{e.step}. {e.name}</td><td>{e.agent ?? "—"}</td>
            <td><span className={`q-pill ${e.status === "ok" ? "ok" : e.status === "skipped" ? "" : "warn"}`}>{e.status}</span></td>
            <td>{e.decision}</td><td className="q-muted" style={{ fontSize: 12 }}>{e.summary}</td></tr>))}
        </tbody>
      </table>
      {!activity.data.length && <p className="q-muted">Aucune activité pour l'instant.</p>}
    </div>
  );
}

export default function AdminApp() {
  const [tab, setTab] = useState("overview");
  const views = { overview: Overview, orders: Orders, alerts: Alerts, users: UsersTab, courses: CoursesTab, activity: ActivityTab };
  const View = views[tab];
  return (
    <AppShell tabs={TABS} active={tab} onTab={setTab} subtitle="Administrateur">
      <div className="q-head"><div><h1>{TABS.find((t) => t.id === tab).label}</h1><div className="q-muted">Tableau de bord administrateur · données de la base 9antra</div></div></div>
      <View key={tab} />
    </AppShell>
  );
}
