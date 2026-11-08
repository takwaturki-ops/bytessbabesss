import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Me() {
  const { user, loading, token, logout } = useAuth();
  const navigate = useNavigate();

  if (loading) return <div className="auth-container">Chargement...</div>;
  if (!token) {
    navigate("/login");
    return null;
  }

  return (
    <div className="auth-container">
      <h1>Me</h1>
      <pre>{JSON.stringify(user, null, 2)}</pre>
      <button
        onClick={() => {
          logout();
          navigate("/login");
        }}
      >
        Logout
      </button>
    </div>
  );
}
