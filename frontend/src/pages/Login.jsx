
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/auth";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const { setUser, setToken } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await login({ email, password });

      setToken(res.data.token);
      localStorage.setItem("smartfin_token", res.data.token);
      setUser(res.data.user || res.data);

      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.error || "Erreur de connexion");
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

        <button type="submit">Se connecter</button>
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
