// API 클라이언트 — JWT 토큰 자동 첨부.
const TOKEN_KEY = "festcast_token";

export function setToken(t: string) {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, t);
}
export function getToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
}
export function clearToken() {
  if (typeof window !== "undefined") localStorage.removeItem(TOKEN_KEY);
}

async function req(path: string, opts: RequestInit = {}) {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as any) };
  const t = getToken();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let msg = `요청 실패 (${res.status})`;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

export const api = {
  register: (b: any) => req("/api/auth/register", { method: "POST", body: JSON.stringify(b) }),
  login: (b: any) => req("/api/auth/login", { method: "POST", body: JSON.stringify(b) }),
  me: () => req("/api/auth/me"),
  projects: () => req("/api/projects"),
  createProject: (b: any) => req("/api/projects", { method: "POST", body: JSON.stringify(b) }),
  predict: (festival: any, projectId?: number) =>
    req(`/api/ai/predict${projectId ? `?project_id=${projectId}` : ""}`,
        { method: "POST", body: JSON.stringify({ festival }) }),
  generate: (b: any) => req("/api/ai/generate", { method: "POST", body: JSON.stringify(b) }),
  modelComparison: () => req("/api/ai/model-comparison"),
  pdf: async (festival: any) => {
    const t = getToken();
    const res = await fetch("/api/reports/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}) },
      body: JSON.stringify({ festival }),
    });
    if (!res.ok) throw new Error("PDF 생성 실패");
    return res.blob();
  },
};
