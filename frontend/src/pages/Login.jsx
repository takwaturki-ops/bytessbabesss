
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, loginTwoFactor } from "../api/auth";
import { extractAccessToken, extractTwoFactorChallenge, getErrorMessage, normalizeOtp } from "../api/authHelpers";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // 2FA: set when the password was correct and the account asks for a 6-digit code.
  const [challengeToken, setChallengeToken] = useState(null);
  const [code, setCode] = useState("");

  const { signIn } = useAuth();
  const navigate = useNavigate();

  const finish = (res) => {
    // Throws if the backend did not return data.accessToken: no token, no login.
    signIn(extractAccessToken(res));
    navigate("/dashboard");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const res = await login({ email, password });
      const challenge = extractTwoFactorChallenge(res);
      if (challenge) {
        setChallengeToken(challenge);
        setCode("");
        return;
      }
      finish(res);
    } catch (err) {
      setError(getErrorMessage(err, "Erreur de connexion"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCode = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      finish(await loginTwoFactor(challengeToken, code));
    } catch (err) {
      const message = getErrorMessage(err, "Code invalide");
      // Expired session or too many attempts: back to the password step.
      if (/sign in again/i.test(message)) {
        setChallengeToken(null);
        setPassword("");
        setError("Session de vérification expirée ou trop de tentatives. Reconnectez-vous.");
      } else {
        setError(message === "Invalid code" ? "Code incorrect. Vérifiez l'heure de votre téléphone et réessayez." : message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (challengeToken) {
    return (
      <div className="auth-container">
        <h1>Vérification en deux étapes</h1>
        <p>Ouvrez votre application d'authentification et entrez le code à 6 chiffres affiché pour 9antra.</p>

        <form onSubmit={handleCode}>
          <label htmlFor="otp">Code de vérification</label>
          <input
            id="otp"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="123456"
            value={code}
            onChange={(e) => setCode(normalizeOtp(e.target.value))}
            autoFocus
            required
          />

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" disabled={submitting || code.length !== 6}>Vérifier</button>
        </form>

        <button
          type="button"
          style={{ marginTop: "12px" }}
          onClick={() => { setChallengeToken(null); setError(""); }}
        >
          Retour
        </button>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <h1>9antra</h1>
      <p>Bienvenue ! Connectez-vous à votre espace.</p>

      <form onSubmit={handleSubmit}>
        <label>Email</label>
        <input
          type="email"
          placeholder="Votre adresse email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <label>Mot de passe</label>
        <input
          type="password"
          placeholder="Votre mot de passe"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && <div className="auth-error">{error}</div>}

        <button type="submit" disabled={submitting}>Se connecter</button>
      </form>

      <p style={{ marginTop: "20px", textAlign: "center" }}>
        Vous n'avez pas encore de compte ?
      </p>

      <button
        type="button"
        onClick={() => navigate("/register")}
      >
        Créer un compte
      </button>
    </div>
  );
}
