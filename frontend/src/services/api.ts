import axios from "axios";

const BASE = import.meta.env.VITE_API_URL ?? "";

const http = axios.create({ baseURL: BASE });

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
  analyze: (data: { cost: number; sell: number; delivery: number; packaging: number }) =>
    http.post("/api/pricing/analyze", data),
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
