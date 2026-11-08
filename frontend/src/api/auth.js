import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:4000/api/auth",
});

export const register = (data) => api.post("/register", data);
export const login = (data) => api.post("/login", data);
export const me = (token) =>
  api.get("/me", { headers: { Authorization: `Bearer ${token}` } });

export default api;
