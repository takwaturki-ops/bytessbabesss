
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/auth";
import { extractAccessToken, getErrorMessage } from "../api/authHelpers";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const res = await login({ email, password });

      // Throws if the backend did not return data.accessToken: no token, no login.
      signIn(extractAccessToken(res));

      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err, "Erreur de connexion"));
    } finally {
      setSubmitting(false);
    }
  };

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
