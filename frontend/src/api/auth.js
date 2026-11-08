import axios from "axios";

import { readToken, resolveApiBaseUrl } from "./authHelpers";

// Backend origin from the environment (frontend/.env: VITE_API_BASE_URL=http://localhost:4000).
const envBaseUrl = import.meta.env?.VITE_API_BASE_URL;
if (!envBaseUrl && import.meta.env?.DEV) {
  console.warn("VITE_API_BASE_URL is not set; using http://localhost:4000 for local development.");
}
export const API_BASE_URL = resolveApiBaseUrl(envBaseUrl);

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/auth`,
  timeout: 10000,
});

// Protected requests: attach the stored token unless the caller already set one.
api.interceptors.request.use((config) => {
  const isPublic = config.url === "/login" || config.url === "/register";
  const token = readToken(window.localStorage);
  if (!isPublic && token && !config.headers?.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const register = (data) => api.post("/register", data);
export const login = (data) => api.post("/login", data);
export const me = (token) =>
  api.get("/me", token ? { headers: { Authorization: `Bearer ${token}` } } : undefined);

export default api;
