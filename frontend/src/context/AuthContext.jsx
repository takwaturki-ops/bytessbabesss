import { createContext, useContext, useState, useEffect } from "react";
import { me } from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(() =>
    localStorage.getItem("smartfin_token")
  );

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    me(token)
      .then((res) => setUser(res.data))
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [token]);

  const value = { user, token, loading, setUser };

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

const useAuth = () => useContext(AuthContext);

export { AuthContext };
export { useAuth };
