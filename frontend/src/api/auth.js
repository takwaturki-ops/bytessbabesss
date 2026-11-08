import axios from "axios";

import { readToken, resolveApiBaseUrl } from "./authHelpers";

// Backend origin. In development it is left empty: requests go to the same URL as the app
// (http://localhost:5173/api/...) and the Vite proxy forwards them to the backend (vite.config.js).
// Set VITE_API_BASE_URL only when the API lives on another origin (for example a deployed backend).
const envBaseUrl = import.meta.env?.VITE_API_BASE_URL;
export const API_BASE_URL = resolveApiBaseUrl(envBaseUrl, import.meta.env?.DEV ? "" : undefined);

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
