// Thin fetch wrapper around the EKIP backend. Every function here maps to
// exactly one API route — no hidden logic, no retries/caching. Keeping this
// dumb on purpose so it's obvious what the backend actually offers.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

let authToken = null;
export function setAuthToken(token) {
  authToken = token;
}

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  if (body && !form) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: form ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  signup: (payload) => request("/auth/signup", { method: "POST", body: payload }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload }),

  listKnowledgeBases: () => request("/knowledge-bases"),
  createKnowledgeBase: (payload) => request("/knowledge-bases", { method: "POST", body: payload }),

  listDocuments: () => request("/documents"),
  getDocument: (id) => request(`/documents/${id}`),
  uploadDocument: (formData) => request("/documents/upload", { method: "POST", body: formData, form: true }),
  deleteDocument: (id) => request(`/documents/${id}`, { method: "DELETE" }),
  listAcl: (id) => request(`/documents/${id}/acl`),

  ask: (payload) => request("/query", { method: "POST", body: payload }),

  listConversations: () => request("/conversations"),
  getConversation: (id) => request(`/conversations/${id}`),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: "DELETE" }),

  getSampleEvalSet: () => request("/eval/sample-set"),
  // Omit `cases` to grade against the bundled sample set.
  runEval: (cases) => request("/eval/run", { method: "POST", body: cases ? { cases } : {} }),
  getQualityDashboard: () => request("/eval/quality"),
  runIsolationCheck: () => request("/admin/security/isolation-check", { method: "POST" }),
  getDependencyAudit: () => request("/admin/security/dependency-audit"),
};
