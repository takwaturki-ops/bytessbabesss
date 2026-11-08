import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Bot, Brain, ChartNoAxesCombined, CreditCard, ShieldCheck, Sparkles, ArrowRight } from "lucide-react";

import { getCourses } from "../api/client";
import { useAuth } from "../context/AuthContext";
import "../styles/mvp.css";

const GREETING = "Ahla bik fi 9antra! Houni l'intelligence tetla9a bel opportunités. Yalla نبداو!";

const AGENTS = [
  { icon: Bot, name: "Sales Agent", text: "Comprend ton besoin, répond à tes objections et te recommande la formation adaptée, au vrai prix du catalogue." },
  { icon: Brain, name: "Customer Intelligence", text: "Analyse la conversation : besoins, motivations, sentiment et niveau d'intérêt." },
  { icon: ShieldCheck, name: "Fraud Agent", text: "Règles de sécurité déterministes : doublons, tentatives répétées, montants incohérents. Le LLM ne peut pas les contourner." },
  { icon: CreditCard, name: "Payment Agent", text: "Valide les preuves du paiement simulé. Jamais de « succès » sans confirmation." },
  { icon: ChartNoAxesCombined, name: "Financial Analyst", text: "Calcule revenus et indicateurs avec pandas, puis les explique simplement." },
];

const STORY = [
  { n: "01", title: "Tu poses ta question", text: "En français, en anglais ou en derja : l'assistant 9antra t'écoute et garde l'historique de vos échanges." },
  { n: "02", title: "Les agents réfléchissent ensemble", text: "Ventes, analyse client, sécurité, paiement et finance collaborent en coulisses, chacun dans son rôle." },
  { n: "03", title: "Tu achètes en toute sécurité", text: "Chaque paiement (simulé) passe d'abord par la détection de fraude. Rien n'est validé sans preuve." },
  { n: "04", title: "Tu suis tout, l'admin aussi", text: "Historique d'achats côté apprenant ; revenus, alertes et activité des agents côté administration." },
];

const reveal = { initial: { opacity: 0, y: 40 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, amount: 0.25 }, transition: { duration: 0.7 } };

function useTyping(text, speed = 38) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);
  return shown;
}

export default function Landing() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const typed = useTyping(GREETING);
  const [courses, setCourses] = useState([]);

  useEffect(() => {
    getCourses().then((list) => setCourses(list.slice(0, 3))).catch(() => setCourses([]));
  }, []);

  const start = () => navigate(token ? "/dashboard" : "/register");

  return (
    <div className="q-root">
      <nav className="q-nav">
        <div className="q-logo"><img src="/mascot.webp" alt="" />9antra</div>
        <div className="q-nav-links">
          <a href="#agents" className="q-btn ghost small hide-sm">Agents IA</a>
          <a href="#histoire" className="q-btn ghost small hide-sm">Comment ça marche</a>
          {token ? (
            <Link to="/dashboard" className="q-btn small">Mon espace</Link>
          ) : (
            <>
              <Link to="/login" className="q-btn ghost small">Connexion</Link>
              <Link to="/register" className="q-btn small">Créer un compte</Link>
            </>
          )}
        </div>
      </nav>

      <header className="q-hero">
        <motion.div initial={{ opacity: 0, x: -40 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8 }}>
          <span className="q-hero-tag"><Sparkles size={15} /> Plateforme d'apprentissage propulsée par 5 agents IA</span>
          <h1>Apprends l'IA.<br /><span className="q-gradient-text">Construis ton avenir.</span></h1>
          <p className="lead">
            9antra (قنطرة) est le pont entre toi et les métiers de l'intelligence artificielle : un assistant qui te conseille,
            des formations concrètes et un achat sécurisé de bout en bout.
          </p>
          <div className="q-hero-cta">
            <button type="button" className="q-btn" onClick={start}>Yalla, on commence <ArrowRight size={18} /></button>
            <a href="#histoire" className="q-btn ghost">Découvrir l'histoire</a>
          </div>
        </motion.div>

        <div className="q-stage">
          <div className="q-orbit" />
          <motion.div className="q-mascot-wrap" initial={{ opacity: 0, scale: 0.6, y: 60 }} animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 90, damping: 12, delay: 0.2 }}>
            <motion.div className="q-bubble" initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.9 }}>
              <small>9antra Bot</small>
              {typed}<span className="q-caret" />
            </motion.div>
            <img className="q-mascot" src="/mascot.webp" alt="Mascotte 9antra, un robot souriant qui salue" />
            <span className="q-wave" role="img" aria-label="salut">👋</span>
          </motion.div>
        </div>
      </header>

      <section className="q-section" id="histoire">
        <motion.div {...reveal}>
          <h2>Une histoire en <span className="q-gradient-text">quatre chapitres</span></h2>
          <p className="sub">De ta première question jusqu'à ton certificat, chaque étape est guidée et protégée.</p>
        </motion.div>
        {STORY.map((s, i) => (
          <motion.div key={s.n} className="q-story" {...reveal} transition={{ duration: 0.6, delay: i * 0.08 }}>
            <div className="num q-gradient-text">{s.n}</div>
            <div className="q-card"><h3 style={{ margin: "0 0 6px" }}>{s.title}</h3><p className="q-muted" style={{ margin: 0 }}>{s.text}</p></div>
          </motion.div>
        ))}
      </section>

      <section className="q-section" id="agents">
        <motion.div {...reveal}>
          <h2>Rencontre les <span className="q-gradient-text">5 agents</span></h2>
          <p className="sub">Chaque agent a un rôle précis. Les décisions de sécurité et de paiement sont prises par des règles vérifiables, pas par le LLM.</p>
        </motion.div>
        <div className="q-grid">
          {AGENTS.map((a, i) => (
            <motion.div key={a.name} className="q-card q-agent" {...reveal} transition={{ duration: 0.6, delay: i * 0.1 }}>
              <div className="icon"><a.icon size={24} /></div>
              <h3>{a.name}</h3>
              <p>{a.text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="q-section">
        <motion.div {...reveal}>
          <h2>Un achat, <span className="q-gradient-text">cinq vérifications</span></h2>
          <p className="sub">Le parcours réel exécuté à chaque achat :</p>
          <div className="q-flow">
            {["Sales", "Customer Intelligence", "Commande", "Fraude", "Paiement", "Finance"].map((s, i, arr) => (
              <span key={s} style={{ display: "contents" }}>
                <span className="step">{s}</span>{i < arr.length - 1 && <ArrowRight className="arrow" size={18} />}
              </span>
            ))}
          </div>
        </motion.div>
      </section>

      {courses.length > 0 && (
        <section className="q-section">
          <motion.div {...reveal}><h2>Quelques <span className="q-gradient-text">formations</span></h2>
            <p className="sub">Catalogue chargé depuis l'API 9antra (données simulées).</p></motion.div>
          <div className="q-grid">
            {courses.map((c, i) => (
              <motion.div key={c.id} className="q-card q-course" {...reveal} transition={{ duration: 0.6, delay: i * 0.1 }}>
                <span className="q-pill">{c.level}</span>
                <h3>{c.title}</h3>
                <p className="q-muted" style={{ margin: 0, fontSize: 14 }}>{c.description}</p>
                <div className="row"><span className="price">{c.priceTnd} TND</span><span className="q-muted">{c.durationWeeks} semaines</span></div>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      <motion.div className="q-cta-band" {...reveal}>
        <h2 style={{ marginTop: 0 }}>Prêt·e à traverser le pont ?</h2>
        <p className="q-muted">Crée ton compte gratuitement et discute avec l'assistant 9antra.</p>
        <button type="button" className="q-btn" onClick={start}>Yalla نبداو <ArrowRight size={18} /></button>
      </motion.div>

      <footer className="q-footer">© 9antra — Prototype hackathon. Paiements et données simulés : aucun argent réel n'est débité.</footer>
    </div>
  );
}
