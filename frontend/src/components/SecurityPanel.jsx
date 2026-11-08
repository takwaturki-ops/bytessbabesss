import { useState } from "react";
import { ShieldCheck, ShieldOff } from "lucide-react";

import { disableTwoFactor, enableTwoFactor, setupTwoFactor } from "../api/auth";
import { getErrorMessage, normalizeOtp } from "../api/authHelpers";
import { useAuth } from "../context/AuthContext";

const ERRORS_FR = {
  "Invalid code": "Code incorrect. Vérifiez l'heure de votre téléphone et réessayez.",
  "Invalid password": "Mot de passe incorrect.",
};
const fr = (err, fallback) => {
  const message = getErrorMessage(err, fallback);
  return ERRORS_FR[message] ?? message;
};

/** "Sécurité" tab: turn two-factor authentication (TOTP) on or off. Shared by the learner and admin spaces. */
export default function SecurityPanel() {
  const { user, setUser } = useAuth();
  const enabled = Boolean(user?.twoFactorEnabled);

  const [enrolment, setEnrolment] = useState(null); // { qrCodeDataUrl, secret } while setting up
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (fn) => {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  const startSetup = () => run(async () => {
    try {
      const res = await setupTwoFactor();
      setEnrolment(res.data.data);
      setCode("");
    } catch (err) {
      setError(fr(err, "Impossible de préparer la double authentification."));
    }
  });

  const confirmSetup = (e) => {
    e.preventDefault();
    return run(async () => {
      try {
        await enableTwoFactor(code);
        setUser({ ...user, twoFactorEnabled: true });
        setEnrolment(null);
        setCode("");
        setNotice("Double authentification activée. Le code vous sera demandé à chaque connexion.");
      } catch (err) {
        setError(fr(err, "Activation impossible."));
      }
    });
  };

  const disable = (e) => {
    e.preventDefault();
    return run(async () => {
      try {
        await disableTwoFactor(password, code);
        setUser({ ...user, twoFactorEnabled: false });
        setPassword("");
        setCode("");
        setNotice("Double authentification désactivée.");
      } catch (err) {
        setError(fr(err, "Désactivation impossible."));
      }
    });
  };

  const codeInput = (
    <input
      className="q-input"
      inputMode="numeric"
      autoComplete="one-time-code"
      placeholder="Code à 6 chiffres"
      value={code}
      onChange={(e) => setCode(normalizeOtp(e.target.value))}
      required
    />
  );

  return (
    <div className="q-card" style={{ maxWidth: 560, display: "grid", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {enabled ? <ShieldCheck size={28} color="#34d399" /> : <ShieldOff size={28} color="#fbbf24" />}
        <div>
          <h2 style={{ margin: 0 }}>Double authentification</h2>
          <div className="q-muted">
            {enabled
              ? "Activée : un code de votre application d'authentification est demandé à chaque connexion."
              : "Désactivée : votre compte n'est protégé que par votre mot de passe."}
          </div>
        </div>
      </div>

      {notice && <div className="q-pill" style={{ justifySelf: "start" }}>{notice}</div>}
      {error && <div className="q-error">{error}</div>}

      {!enabled && !enrolment && (
        <button type="button" className="q-btn" disabled={busy} onClick={startSetup} style={{ justifySelf: "start" }}>
          Activer la double authentification
        </button>
      )}

      {!enabled && enrolment && (
        <form onSubmit={confirmSetup} style={{ display: "grid", gap: 12 }}>
          <ol className="q-muted" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.6 }}>
            <li>Installez une application d'authentification (Google Authenticator, Microsoft Authenticator…).</li>
            <li>Scannez ce QR code avec l'application.</li>
            <li>Entrez le code à 6 chiffres qu'elle affiche.</li>
          </ol>
          <img src={enrolment.qrCodeDataUrl} alt="QR code à scanner avec votre application d'authentification"
            width={200} height={200} style={{ background: "#fff", borderRadius: 12, padding: 8 }} />
          <div className="q-muted" style={{ fontSize: 13 }}>
            Impossible de scanner ? Saisissez cette clé dans l'application :
            <code style={{ display: "block", marginTop: 4, wordBreak: "break-all", userSelect: "all" }}>{enrolment.secret}</code>
          </div>
          {codeInput}
          <div style={{ display: "flex", gap: 8 }}>
            <button type="submit" className="q-btn" disabled={busy || code.length !== 6}>Confirmer et activer</button>
            <button type="button" className="q-btn ghost" disabled={busy} onClick={() => { setEnrolment(null); setError(""); }}>Annuler</button>
          </div>
        </form>
      )}

      {enabled && (
        <form onSubmit={disable} style={{ display: "grid", gap: 12 }}>
          <div className="q-muted">Pour désactiver, confirmez avec votre mot de passe et un code de l'application.</div>
          <input
            className="q-input"
            type="password"
            autoComplete="current-password"
            placeholder="Mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {codeInput}
          <button type="submit" className="q-btn danger" disabled={busy || code.length !== 6 || !password} style={{ justifySelf: "start" }}>
            Désactiver
          </button>
        </form>
      )}
    </div>
  );
}
