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

export type CcHistoryEntry = {
  cc_session_id: string;
  mtime: number;
  size_bytes: number;
  first_user: string;
  user_turns: number;
  assistant_turns: number;
};

export type HistoryMessage = {
  kind: "user" | "assistant" | "tool_use" | "thinking";
  text: string;
  ts?: number | null;
  tool?: string | null;
};

export type GeneratedDoc = {
  filename: string;
  url: string;
  exists: boolean;
  last_touched: number;
};

export type TaskKind = "poi" | "gameplay" | "prop";

export type WorkspaceTask = {
  name: string;
  path: string;
  kind: TaskKind;
  desc: string;
  status: string;
  created_at: number;
  doc_count: number;
  material_count: number;
  session_count: number;
  children: WorkspaceTask[];
};

export type WorkspaceTree = {
  root: string;
  initialized: boolean;
  tasks: WorkspaceTask[];
};

export type DesignerProfile = {
  designer_cn: string;
  designer_en_short: string;
  designer_full_en: string;
  notes: string;
  updated_at?: number;
};

export type TaskDetail = {
  name: string;
  path: string;
  kind: TaskKind;
  desc: string;
  status: string;
  created_at: number;
  docs: { filename: string; size_bytes: number; mtime: number }[];
  materials: { filename: string; size_bytes: number; mtime: number }[];
  sessions: { cc_session_id: string; note: string; linked_at: number }[];
};

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
  createSession: (opts?: { client_id?: string; namespace?: string; cc_session_id?: string }) =>
    request<SessionRecord>("/api/sessions", { method: "POST", body: JSON.stringify(opts ?? {}) }),

  // ── CC history ────────────────────────────────────────────────────────
  listCcHistory: (limit = 30) =>
    request<CcHistoryEntry[]>(`/api/cc-history?limit=${limit}`),
  getCcHistoryMessages: (cc_session_id: string) =>
    request<HistoryMessage[]>(`/api/cc-history/${encodeURIComponent(cc_session_id)}/messages`),
  getCcHistoryGeneratedDocs: (cc_session_id: string) =>
    request<GeneratedDoc[]>(`/api/cc-history/${encodeURIComponent(cc_session_id)}/generated-docs`),

  // ── Workspace ─────────────────────────────────────────────────────────
  getWorkspace: () =>
    request<WorkspaceTree>("/api/workspace"),
  createTask: (body: { name: string; kind: "poi" | "gameplay" | "prop"; desc?: string; parent_path?: string }) =>
    request<{ path: string; abs_path: string }>("/api/workspace/tasks", {
      method: "POST", body: JSON.stringify(body),
    }),
  deleteTask: (task_path: string) =>
    request<{ ok: true; deleted: string }>(`/api/workspace/tasks/${task_path.split("/").map(encodeURIComponent).join("/")}`, {
      method: "DELETE",
    }),
  getTask: (task_path: string) =>
    request<TaskDetail>(`/api/workspace/tasks/${task_path.split("/").map(encodeURIComponent).join("/")}`),
  linkDocToTask: (task_path: string, src_filename: string, move = true) =>
    request<{ ok: true }>(`/api/workspace/tasks/${task_path.split("/").map(encodeURIComponent).join("/")}/link-doc`, {
      method: "POST", body: JSON.stringify({ src_filename, move }),
    }),
  importSpecs: () =>
    request<{ created_tasks: string[]; imported_specs: { spec_id: string; task_path: string }[]; skipped: { spec_id: string; reason: string }[] }>(
      "/api/workspace/import-specs", { method: "POST" },
    ),
  importDocs: () =>
    request<{ imported_docs: { filename: string; task_path: string }[]; skipped: { filename: string; reason: string }[] }>(
      "/api/workspace/import-docs", { method: "POST" },
    ),

  // ── Storyboard ────────────────────────────────────────────────────────
  getBeats: (level_id: string) =>
    request<{ level_id: string; spec_id: string; nodes: Array<{ id: string; type: string; label: string; notes?: string; phase?: string; zone_id?: string }> }>(
      `/api/storyboard/beats?level_id=${encodeURIComponent(level_id)}`
    ),
  composePrompts: (spec_id: string) =>
    request<{ panels: { panel_id: string; title: string; prompt: string; negative_prompt: string }[] }>(
      "/api/storyboard/compose-prompts", { method: "POST", body: JSON.stringify({ spec_id }) },
    ),
  uploadStoryboardImage: async (spec_id: string, panel_id: string, file: File): Promise<{ relative_path: string; panel_id: string }> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`/api/storyboard/upload-image?spec_id=${encodeURIComponent(spec_id)}&panel_id=${encodeURIComponent(panel_id)}`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { const body = await res.json(); if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail); } catch { /* ignore */ }
      throw new ApiError(res.status, `${res.status} ${detail}`);
    }
    return res.json() as Promise<{ relative_path: string; panel_id: string }>;
  },

  // ── Designer profile ─────────────────────────────────────────────────
  getProfile: () => request<DesignerProfile>("/api/profile"),
  updateProfile: (body: DesignerProfile) =>
    request<DesignerProfile>("/api/profile", { method: "PUT", body: JSON.stringify(body) }),
  listSessions: () =>
    request<{ sessions: SessionRecord[] }>("/api/sessions"),
  endSession: (client_id: string) =>
    request<{ ok: true }>(`/api/sessions/${encodeURIComponent(client_id)}`, { method: "DELETE" }),
  sendMessage: (client_id: string, text: string, spec_id?: string) =>
    request<MessageQueued>(`/api/sessions/${encodeURIComponent(client_id)}/messages`, {
      method: "POST",
      body: JSON.stringify({ text, ...(spec_id ? { spec_id } : {}) }),
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
