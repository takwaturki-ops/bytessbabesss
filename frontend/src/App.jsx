
import { Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";

import Login from "./pages/Login";
import Register from "./pages/Register";
import Me from "./pages/Me";
import Landing from "./pages/Landing";
import UserApp from "./pages/UserApp";
import AdminApp from "./pages/AdminApp";
import "./styles/mvp.css";

function Loading() {
  return <div className="q-root" style={{ display: "grid", placeItems: "center" }}><p className="q-muted">Chargement…</p></div>;
}

// UX guard only: every protected API route is enforced by the backend (JWT + role read from the database).
function RequireAuth({ role, children }) {
  const { token, user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!token) return <Navigate to="/login" replace />;
  if (!user) return <Loading />;
  if (role && user.role !== role) return <Navigate to="/dashboard" replace />;
  return children;
}

function DashboardRoute() {
  const { token, user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!token) return <Navigate to="/login" replace />;
  if (!user) return <Loading />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/app"} replace />;
}

function AuthPage({ children }) {
  return (
    <div className="q-root q-auth-page">
      <div style={{ width: "min(420px, 100%)" }}>
        <Link to="/"><img className="q-auth-mascot" src="/mascot.webp" alt="Retour à l'accueil 9antra" /></Link>
        {children}
      </div>
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<AuthPage><Login /></AuthPage>} />
      <Route path="/register" element={<AuthPage><Register /></AuthPage>} />
      <Route path="/me" element={<Me />} />
      <Route path="/dashboard" element={<DashboardRoute />} />
      <Route path="/app" element={<RequireAuth role="customer"><UserApp /></RequireAuth>} />
      <Route path="/admin" element={<RequireAuth role="admin"><AdminApp /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
