// API client for the 9antra backend (the browser never talks to the AI service directly).
import axios from "axios";

import { API_BASE_URL } from "./auth";
import { readToken } from "./authHelpers";

const api = axios.create({ baseURL: `${API_BASE_URL}/api`, timeout: 60000 });

api.interceptors.request.use((config) => {
  const token = readToken(window.localStorage);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

const data = (p) => p.then((res) => res.data.data);

export const getCourses = () => data(api.get("/courses"));
export const getCourse = (id) => data(api.get(`/courses/${id}`));

export const listConversations = () => data(api.get("/conversations"));
export const createConversation = () => data(api.post("/conversations", {}));
export const getMessages = (id) => data(api.get(`/conversations/${id}/messages`));
export const sendMessage = (id, content) => data(api.post(`/conversations/${id}/messages`, { content }));

export const createPurchase = (body) => data(api.post("/purchases", body));
export const listPurchases = () => data(api.get("/purchases"));
export const getPurchase = (id) => data(api.get(`/purchases/${id}`));

export const admin = {
  stats: () => data(api.get("/admin/stats")),
  insights: () => data(api.get("/admin/insights")),
  users: () => data(api.get("/admin/users")),
  setRole: (id, role) => data(api.patch(`/admin/users/${id}/role`, { role })),
  courses: () => data(api.get("/admin/courses")),
  updateCourse: (id, body) => data(api.patch(`/admin/courses/${id}`, body)),
  orders: () => data(api.get("/admin/orders")),
  order: (id) => data(api.get(`/admin/orders/${id}`)),
  alerts: () => data(api.get("/admin/alerts")),
  decide: (id, decision) => data(api.post(`/admin/alerts/${id}/decision`, { decision })),
  activity: () => data(api.get("/admin/agent-activity")),
};

export const PAYMENT_SCENARIOS = [
  { value: "success", label: "Paiement accepté" },
  { value: "failed", label: "Carte refusée" },
  { value: "pending", label: "Paiement en attente" },
  { value: "suspicious_location", label: "Localisation suspecte (validation humaine)" },
  { value: "repeated_attempts", label: "Tentatives répétées (validation humaine)" },
  { value: "amount_mismatch", label: "Montant incohérent (validation humaine)" },
  { value: "invalid_signature", label: "Signature invalide (bloqué)" },
  { value: "duplicate", label: "Paiement en double (bloqué)" },
];

export const STATUS_LABELS = {
  paid: { label: "Payé", tone: "ok" },
  failed: { label: "Échoué", tone: "bad" },
  pending: { label: "En attente", tone: "warn" },
  requires_review: { label: "Vérification", tone: "warn" },
  awaiting_approval: { label: "Validation humaine", tone: "warn" },
  blocked: { label: "Bloqué (fraude)", tone: "bad" },
  approved_awaiting_payment: { label: "Approuvé, paiement à refaire", tone: "warn" },
  rejected: { label: "Rejeté", tone: "bad" },
};

export const FINAL_STATUS_TEXT = {
  completed: { title: "Achat confirmé !", text: "Paiement validé, accès au cours activé.", tone: "ok" },
  payment_failed: { title: "Paiement refusé", text: "Aucun montant débité. Réessayez avec un autre moyen.", tone: "bad" },
  payment_pending: { title: "Paiement en attente", text: "Le prestataire n'a pas encore confirmé.", tone: "warn" },
  payment_requires_review: { title: "Paiement en vérification", text: "Les preuves de paiement doivent être vérifiées.", tone: "warn" },
  awaiting_human_approval: { title: "Validation humaine requise", text: "Notre équipe sécurité doit approuver cette opération.", tone: "warn" },
  blocked_by_fraud: { title: "Opération bloquée", text: "Les règles de sécurité ont bloqué ce paiement. Rien n'a été débité.", tone: "bad" },
  no_purchase: { title: "Aucun achat", text: "La commande n'a pas été créée.", tone: "warn" },
};

export default api;
