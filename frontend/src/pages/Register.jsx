import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { register } from "../api/auth";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { setUser, setToken } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await register({ email, password });
      setToken(res.data.token);
      localStorage.setItem("smartfin_token", res.data.token);
      setUser(res.data.user || res.data);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.error || "Erreur register");
    }
  };

  return (
    <div className="auth-container">
      <h1>SmartFin AI</h1>
      <form onSubmit={handleSubmit}>
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
          required
        />
        {error && <div className="auth-error">{error}</div>}
        <button type="submit">S'inscrire</button>
      </form>
    </div>
  );
}
