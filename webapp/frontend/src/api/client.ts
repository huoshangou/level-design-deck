// 统一 fetch wrapper：自动加 Content-Type、报错带 backend 返回的 detail。
// 所有路径都走 /api/* 走 Vite proxy (dev) 或同源 (prod)。

import type {
  CheckResult,
  CrossCheckResult,
  Health,
  ModuleInfo,
  RenderDeckResult,
  RenderLevelResult,
  RenderResult,
  SaveResult,
  SpecInfo,
  SpecRecord,
} from "./types";
import type { AttachedFile, MessageQueued, SessionRecord } from "./chat-types";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // ignore
    }
    throw new ApiError(res.status, `${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),

  listSpecs: () => request<{ specs: SpecInfo[] }>("/api/specs"),
  getSpec: (id: string) => request<SpecRecord>(`/api/specs/${encodeURIComponent(id)}`),
  saveSpec: (id: string, content: Record<string, unknown>) =>
    request<SaveResult>(`/api/specs/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  deleteSpec: (id: string) =>
    request<{ ok: true }>(`/api/specs/${encodeURIComponent(id)}`, { method: "DELETE" }),

  listModules: () => request<{ modules: ModuleInfo[] }>("/api/modules"),
  getModuleSchema: (name: string) =>
    request<Record<string, unknown>>(`/api/modules/${encodeURIComponent(name)}/schema`),

  checkSpec: (spec_id: string) =>
    request<CheckResult>("/api/check", { method: "POST", body: JSON.stringify({ spec_id }) }),
  crossCheck: (level_id: string) =>
    request<CrossCheckResult>("/api/cross-check", { method: "POST", body: JSON.stringify({ level_id }) }),

  renderSpec: (spec_id: string) =>
    request<RenderResult>("/api/render", { method: "POST", body: JSON.stringify({ spec_id }) }),
  renderLevel: (level_id: string, render_missing = true) =>
    request<RenderLevelResult>("/api/render-level", {
      method: "POST",
      body: JSON.stringify({ level_id, render_missing }),
    }),
  renderDeck: (level_id: string) =>
    request<RenderDeckResult>("/api/render-deck", { method: "POST", body: JSON.stringify({ level_id }) }),

  // ── Chat / Sessions ────────────────────────────────────────────────────
  createSession: (opts?: { client_id?: string; namespace?: string }) =>
    request<SessionRecord>("/api/sessions", { method: "POST", body: JSON.stringify(opts ?? {}) }),
  listSessions: () =>
    request<{ sessions: SessionRecord[] }>("/api/sessions"),
  endSession: (client_id: string) =>
    request<{ ok: true }>(`/api/sessions/${encodeURIComponent(client_id)}`, { method: "DELETE" }),
  sendMessage: (client_id: string, text: string) =>
    request<MessageQueued>(`/api/sessions/${encodeURIComponent(client_id)}/messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  uploadFile: async (client_id: string, file: File): Promise<AttachedFile> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`/api/sessions/${encodeURIComponent(client_id)}/files`, {
      method: "POST",
      body: form,
      // no Content-Type header — browser sets multipart boundary automatically
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      } catch { /* ignore */ }
      throw new ApiError(res.status, `${res.status} ${detail}`);
    }
    return res.json() as Promise<AttachedFile>;
  },

  listFiles: (client_id: string) =>
    request<{ files: AttachedFile[] }>(`/api/sessions/${encodeURIComponent(client_id)}/files`),

  deleteFile: (client_id: string, file_id: string) =>
    request<{ ok: true }>(`/api/sessions/${encodeURIComponent(client_id)}/files/${encodeURIComponent(file_id)}`, {
      method: "DELETE",
    }),
};

export { ApiError };
