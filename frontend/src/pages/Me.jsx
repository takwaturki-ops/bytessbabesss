import { useAuth } from "../context/AuthContext";
import { Navigate, useNavigate } from "react-router-dom";

export default function Me() {
  const { user, loading, token, logout } = useAuth();
  const navigate = useNavigate();

  if (loading) return <div className="auth-container">Chargement...</div>;
  if (!token) {
    return <Navigate to="/login" replace />;
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
