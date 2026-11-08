import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../api/auth";
import { extractAccessToken, getErrorMessage } from "../api/authHelpers";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const [name, setName] = useState("");
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
      // Registration returns the created user (no token); then log in with the same credentials.
      await register({ name, email, password });
      const res = await login({ email, password });
      signIn(extractAccessToken(res));
      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors de l'inscription"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <h1>SmartFin AI</h1>
      <form onSubmit={handleSubmit}>
        <label>Nom</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          minLength={2}
          maxLength={100}
          required
        />
        <label>Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label>Mot de passe</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />
        {error && <div className="auth-error">{error}</div>}
        <button type="submit" disabled={submitting}>S'inscrire</button>
      </form>
    </div>
  );
}
