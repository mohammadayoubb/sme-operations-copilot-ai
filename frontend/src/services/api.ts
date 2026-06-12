import axios from "axios";

// Strip any trailing slash so `${BASE}/api/...` can never become `//api/...`
// (a double slash 404s on the backend).
const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");

const http = axios.create({ baseURL: BASE });

// Attach stored JWT to every request
http.interceptors.request.use((config) => {
  const token = localStorage.getItem("soukpilot_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear token and redirect to login (skip for the login endpoint itself)
http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (
      err.response?.status === 401 &&
      !err.config?.url?.includes("/api/auth/login")
    ) {
      localStorage.removeItem("soukpilot_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  login: (username: string, password: string) =>
    http.post<{ access_token: string; token_type: string; username: string; business_id: number | null; role: string | null }>(
      "/api/auth/login",
      { username, password }
    ),
  register: (businessName: string, username: string, password: string) =>
    http.post<{ access_token: string; token_type: string; username: string; business_id: number }>(
      "/api/auth/register",
      { business_name: businessName, username, password }
    ),
};

export const invoicesApi = {
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return http.post("/api/invoices/upload", fd);
  },
  list: () => http.get("/api/invoices/"),
  get: (id: number) => http.get(`/api/invoices/${id}`),
  status: (id: number) => http.get(`/api/invoices/${id}/status`),
};

export const ordersApi = {
  extract: (message: string, source = "whatsapp") =>
    http.post("/api/orders/extract", { message, source }),
  list: () => http.get("/api/orders/"),
  reviewQueue: () => http.get("/api/orders/review-queue"),
  approve: (id: number) => http.post(`/api/orders/${id}/approve`),
  reject: (id: number) => http.post(`/api/orders/${id}/reject`),
  updateStatus: (id: number, status: string) =>
    http.patch(`/api/orders/${id}/status`, { status }),
};

export const productsApi = {
  list: () => http.get("/api/products/"),
  get: (id: number) => http.get(`/api/products/${id}`),
  adjustStock: (id: number, delta: number, reason: string) =>
    http.patch(`/api/products/${id}/stock`, { delta, reason }),
};

export const pricingApi = {
  products: () => http.get("/api/pricing/products"),
  analyze: (data: {
    cost: number; sell: number; delivery: number; packaging: number;
    product_id?: number | null; product_name?: string | null;
  }) => http.post("/api/pricing/analyze", data),
  history: (productId: number) => http.get(`/api/pricing/history/${productId}`),
};

export const forecastApi = {
  reorder: () => http.get("/api/forecast/reorder"),
  stockout: (productId: number) => http.get(`/api/forecast/stockout/${productId}`),
};

export const qaApi = {
  ask: (question: string) => http.post("/api/qa/ask", { question }),
  index: () => http.post("/api/qa/index"),
};

export const reportsApi = {
  list: () => http.get("/api/reports/"),
  latest: () => http.get("/api/reports/latest"),
  generate: () => http.post("/api/reports/generate"),
  exportPdf: (id: number) =>
    http.get(`/api/reports/${id}/pdf`, { responseType: "text" }),
};

export const agentApi = {
  chat: (message: string, history: { role: string; content: string }[]) =>
    http.post("/api/agent/chat", { message, history }),
};

export const anomalyApi = {
  alerts: () => http.get("/api/anomaly/alerts"),
};

export const driftApi = {
  latest: () => http.get("/api/drift/latest"),
  run: () => http.post("/api/drift/run"),
};

// ── Superadmin API (uses a separate token stored under soukpilot_admin_token) ─

const adminHttp = axios.create({ baseURL: BASE });
adminHttp.interceptors.request.use((config) => {
  const token = localStorage.getItem("soukpilot_admin_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export interface TenantStats {
  orders: { total: number; by_status: Record<string, number>; last_at: string | null };
  invoices: { total: number; by_status: Record<string, number>; last_at: string | null };
  products: { total: number; low_stock: number };
  revenue_total: number;
  ai: { insights_generated: number; documents_indexed: number };
  users: { total: number; by_role: Record<string, number> };
  last_activity_at: string | null;
}

export interface TenantInfo {
  id: number;
  name: string;
  created_at: string | null;
  owner_username: string | null;
  user_count: number;
  product_count: number;
  order_count: number;
}

export const adminApi = {
  login: (username: string, password: string) =>
    http.post<{ access_token: string; username: string; business_id: number | null; role: string | null }>(
      "/api/auth/login",
      { username, password }
    ),
  tenants: () => adminHttp.get<TenantInfo[]>("/api/admin/tenants"),
  createTenant: (data: { business_name: string; username: string; password: string }) =>
    adminHttp.post<{ id: number; name: string; owner_username: string }>("/api/admin/tenants", data),
  deleteTenant: (businessId: number) =>
    adminHttp.delete(`/api/admin/tenants/${businessId}`),
  tenantStats: (businessId: number) =>
    adminHttp.get<TenantStats>(`/api/admin/tenants/${businessId}/stats`),
};

export const voiceApi = {
  transcribe: (file: File) => {
    const fd = new FormData();
    fd.append("audio", file);
    return http.post("/api/voice/transcribe", fd);
  },
  command: (transcript: string) => http.post("/api/voice/command", { transcript }),
  speak: (text: string) =>
    http.post("/api/voice/speak", { text }, { responseType: "arraybuffer" }),
};
