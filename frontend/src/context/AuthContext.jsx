
import { createContext, useContext, useState, useEffect } from "react";
import { me } from "../api/auth";
import { clearToken, readToken, writeToken } from "../api/authHelpers";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const [token, setToken] = useState(() => readToken(window.localStorage));

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    setLoading(true);

    me(token)
      .then((res) => {
        // Backend: { status: "ok", data: { userId, id, name, email, role, createdAt } }
        setUser(res.data?.data ?? null);
      })
      .catch((err) => {
        // Only an authentication failure ends the session; a network error keeps the token.
        if (err?.response?.status === 401) {
          clearToken(window.localStorage);
          setToken(null);
        }
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  // Store a token received from the backend and start the session (/me is then loaded automatically).
  const signIn = (newToken) => {
    writeToken(window.localStorage, newToken);
    setToken(newToken);
  };

  const logout = () => {
    clearToken(window.localStorage);
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    setUser,
    setToken,
    signIn,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
