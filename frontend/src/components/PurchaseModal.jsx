import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2, X } from "lucide-react";

import { FINAL_STATUS_TEXT, PAYMENT_SCENARIOS, createPurchase } from "../api/client";
import { getErrorMessage } from "../api/authHelpers";
import { AgentPipeline, AgentSummary } from "./ui";

/** Simulated checkout: runs the real five-agent workflow through the backend (POST /api/purchases). */
export default function PurchaseModal({ course, conversationId, onClose, onDone }) {
  const [scenario, setScenario] = useState("success");
  const [method, setMethod] = useState("card");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const pay = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await createPurchase({
        course_id: course.id ?? course.course_id,
        payment_scenario: scenario,
        payment_method: method,
        ...(conversationId ? { conversation_id: conversationId } : {}),
      });
      setResult(res);
      onDone?.(res);
    } catch (err) {
      setError(getErrorMessage(err, "L'achat n'a pas pu être traité."));
    } finally {
      setBusy(false);
    }
  };

  const outcome = result && FINAL_STATUS_TEXT[result.finalStatus];
  return (
    <div className="q-modal-bg" role="dialog" aria-modal="true" aria-label="Achat simulé">
      <motion.div className="q-card q-modal" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}>
        <div className="q-head" style={{ marginBottom: 10 }}>
          <div>
            <div className="q-muted" style={{ fontSize: 13 }}>Achat simulé</div>
            <h2 style={{ margin: 0 }}>{course.title}</h2>
          </div>
          <button type="button" className="q-btn ghost small" onClick={onClose} aria-label="Fermer"><X size={16} /></button>
        </div>
        <div style={{ fontSize: 28, fontWeight: 800, color: "var(--cyan)" }}>{course.priceTnd ?? course.price_tnd} TND</div>

        {!result && (
          <>
            <div className="q-two" style={{ marginTop: 16 }}>
              <label>Moyen de paiement
                <select className="q-select" value={method} onChange={(e) => setMethod(e.target.value)} disabled={busy}>
                  <option value="card">Carte</option><option value="mobile_wallet">Portefeuille mobile</option><option value="bank_transfer">Virement</option>
                </select>
              </label>
              <label>Scénario de démonstration
                <select className="q-select" value={scenario} onChange={(e) => setScenario(e.target.value)} disabled={busy}>
                  {PAYMENT_SCENARIOS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </label>
            </div>
            <p className="q-notice">Paiement SIMULÉ : aucun argent réel n'est débité. Le scénario choisit la réponse du prestataire fictif ; les décisions sont prises par les agents.</p>
            {error && <div className="q-error">{error}</div>}
            <button type="button" className="q-btn" onClick={pay} disabled={busy} style={{ marginTop: 12 }}>
              {busy ? <><Loader2 size={16} className="spin" /> Les 5 agents traitent votre achat…</> : "Confirmer l'achat"}
            </button>
          </>
        )}

        {result && (
          <>
            <div className={`q-result ${outcome?.tone ?? "warn"}`}>
              <div style={{ fontWeight: 800, fontSize: 18 }}>{outcome?.title ?? result.finalStatus}</div>
              <div>{result.agents?.payment?.customerMessage ?? outcome?.text}</div>
              <div className="q-muted" style={{ fontSize: 12, marginTop: 6 }}>
                Commande {result.orderId ?? "—"} · Transaction {result.transactionId ?? "non créée"} · Workflow {result.workflowId}
              </div>
            </div>
            <h3 style={{ marginBottom: 0 }}>Activité des agents</h3>
            <AgentPipeline trace={result.trace} />
            <AgentSummary agents={result.agents} />
            <p className="q-notice">{result.dataNotice} Mode IA : {result.llmMode}.</p>
            <button type="button" className="q-btn" onClick={onClose}>Fermer</button>
          </>
        )}
      </motion.div>
    </div>
  );
}
