import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Request interceptor - attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("omms_access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor - handle auth errors
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("omms_access_token");
      localStorage.removeItem("omms_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── AUTH ──────────────────────────────────────────────────────
export const authAPI = {
  login: (data) => api.post("/auth/login", data),
  register: (data) => api.post("/auth/register", data),
  me: () => api.get("/auth/me"),
  changePassword: (old_password, new_password) =>
    api.post("/auth/change-password", null, { params: { old_password, new_password } }),
};

// ── DASHBOARD ─────────────────────────────────────────────────
export const dashboardAPI = {
  stats: (project_id) => api.get("/dashboard/stats", { params: { project_id } }),
  woTrend: (project_id, months = 6) =>
    api.get("/dashboard/charts/work-orders-trend", { params: { project_id, months } }),
  assetStatus: (project_id) =>
    api.get("/dashboard/charts/asset-status", { params: { project_id } }),
  costTrend: (project_id, months = 6) =>
    api.get("/dashboard/charts/cost-trend", { params: { project_id, months } }),
};

// ── PROJECTS ──────────────────────────────────────────────────
export const projectsAPI = {
  list: (params) => api.get("/projects", { params }),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post("/projects", data),
  update: (id, data) => api.put(`/projects/${id}`, data),
};

// ── ASSETS ───────────────────────────────────────────────────
export const assetsAPI = {
  list: (params) => api.get("/assets", { params }),
  get: (id) => api.get(`/assets/${id}`),
  create: (data) => api.post("/assets", data),
  update: (id, data) => api.put(`/assets/${id}`, data),
  delete: (id) => api.delete(`/assets/${id}`),
  qrCode: (id) => api.get(`/assets/${id}/qr-code`),
  history: (id) => api.get(`/assets/${id}/history`),
  updateHours: (id, hours) =>
    api.patch(`/assets/${id}/update-hours`, null, { params: { running_hours: hours } }),
};

// ── MAINTENANCE PLANS ────────────────────────────────────────
export const maintenancePlansAPI = {
  list: (params) => api.get("/maintenance-plans", { params }),
  create: (data) => api.post("/maintenance-plans", data),
  generateWO: (id) => api.post(`/maintenance-plans/${id}/generate-work-order`),
};

// ── WORK ORDERS ──────────────────────────────────────────────
export const workOrdersAPI = {
  list: (params) => api.get("/work-orders", { params }),
  get: (id) => api.get(`/work-orders/${id}`),
  create: (data) => api.post("/work-orders", data),
  update: (id, data) => api.put(`/work-orders/${id}`, data),
  assign: (id, technician_id) =>
    api.patch(`/work-orders/${id}/assign`, null, { params: { technician_id } }),
  complete: (id, notes, hours) =>
    api.patch(`/work-orders/${id}/complete`, null, {
      params: { completion_notes: notes, actual_duration_hours: hours },
    }),
  stats: (project_id) => api.get("/work-orders/stats/summary", { params: { project_id } }),
};

// ── INVENTORY ────────────────────────────────────────────────
export const inventoryAPI = {
  listParts: (params) => api.get("/inventory/spare-parts", { params }),
  createPart: (data) => api.post("/inventory/spare-parts", data),
  transaction: (id, qty, type, notes) =>
    api.post(`/inventory/spare-parts/${id}/transaction`, null, {
      params: { qty, tx_type: type, notes },
    }),
  alerts: () => api.get("/inventory/alerts"),
};

// ── CONTRACTS ────────────────────────────────────────────────
export const contractsAPI = {
  list: (params) => api.get("/contracts", { params }),
  create: (data) => api.post("/contracts", data),
  expiring: (days = 30) => api.get("/contracts/expiring", { params: { days } }),
};

// ── HSE ──────────────────────────────────────────────────────
export const hseAPI = {
  listIncidents: (params) => api.get("/hse/incidents", { params }),
  createIncident: (data) => api.post("/hse/incidents", data),
  listPermits: (params) => api.get("/hse/permits", { params }),
  createPermit: (data) => api.post("/hse/permits", data),
  stats: (project_id) => api.get("/hse/stats", { params: { project_id } }),
};

// ── QUALITY ──────────────────────────────────────────────────
export const qualityAPI = {
  listNCR: (params) => api.get("/quality/ncr", { params }),
  createNCR: (data) => api.post("/quality/ncr", data),
  listInspections: (params) => api.get("/quality/inspections", { params }),
  stats: (project_id) => api.get("/quality/stats", { params: { project_id } }),
};

// ── BUDGET ───────────────────────────────────────────────────
export const budgetAPI = {
  listPlans: (params) => api.get("/budget/plans", { params }),
  createPlan: (data) => api.post("/budget/plans", data),
  addCost: (data) => api.post("/budget/transactions", data),
  summary: (project_id, year) =>
    api.get("/budget/summary", { params: { project_id, year } }),
};

// ── REPORTS ──────────────────────────────────────────────────
export const reportsAPI = {
  maintenanceSummary: (params) => api.get("/reports/maintenance-summary", { params }),
  kpi: (params) => api.get("/reports/kpi", { params }),
};

// ── NOTIFICATIONS ────────────────────────────────────────────
export const notificationsAPI = {
  list: (unread_only = false) => api.get("/notifications", { params: { unread_only } }),
  markRead: (id) => api.patch(`/notifications/${id}/read`),
  markAllRead: () => api.patch("/notifications/mark-all-read"),
  unreadCount: () => api.get("/notifications/unread-count"),
};

// ── USERS ────────────────────────────────────────────────────
export const usersAPI = {
  list: (params) => api.get("/users", { params }),
  get: (id) => api.get(`/users/${id}`),
  update: (id, data) => api.put(`/users/${id}`, data),
};

export default api;
