
import { createContext, useContext, useState, useEffect } from "react";
import { me } from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const [token, setToken] = useState(() =>
    localStorage.getItem("smartfin_token")
  );

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
        setUser(res.data);
      })
      .catch(() => {
        localStorage.removeItem("smartfin_token");
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  const logout = () => {
    localStorage.removeItem("smartfin_token");
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    setUser,
    setToken,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
