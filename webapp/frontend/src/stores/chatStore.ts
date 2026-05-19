// Chat client-side state：session、消息列表、WS 连接状态、流式累积。
// Server state 走 useChatSocket hook，store 只管 UI state。

import { create } from "zustand";
import { api } from "../api/client";
import { useEditorStore } from "./editorStore";
import type { AttachedFile, WsEnvelope } from "../api/chat-types";

export type ChatMessage =
  | { kind: "user"; text: string; ts: number }
  | { kind: "assistant"; text: string; cost_usd?: number; duration_ms?: number; ts: number }
  | { kind: "thinking"; text: string; ts: number }
  | { kind: "tool_use"; tool: string; args: unknown; ts: number }
  | { kind: "error"; message: string; ts: number }
  | { kind: "hint"; text: string; ts: number };

export type WsState = "idle" | "connecting" | "open" | "closed";

type ChatState = {
  clientId: string | null;
  messages: ChatMessage[];
  wsState: WsState;
  pendingAssistant: string;
  isStreaming: boolean;
  attachedFiles: AttachedFile[];
  uploadingFiles: string[];
  _lastSendTs: number;
  inputPrefill: string | null; // 预填充输入框内容，消费后置 null

  initSession: () => Promise<void>;
  addUserMessage: (text: string) => void;
  handleEvent: (envelope: WsEnvelope) => void;
  markStreamComplete: () => void;
  setWsState: (state: WsState) => void;
  triggerDocFill: (kind: string, label: string) => void;
  clearInputPrefill: () => void;
  reset: () => void;
  uploadFile: (file: File) => Promise<void>;
  removeAttachedFile: (file_id: string) => Promise<void>;
  reloadAttachedFiles: () => Promise<void>;
};

export const useChatStore = create<ChatState>((set, get) => ({
  clientId: null,
  messages: [],
  wsState: "idle",
  pendingAssistant: "",
  isStreaming: false,
  attachedFiles: [],
  uploadingFiles: [],
  _lastSendTs: 0,
  inputPrefill: null,

  initSession: async () => {
    const record = await api.createSession();
    set({
      clientId: record.client_id,
      messages: [],
      pendingAssistant: "",
      isStreaming: false,
      wsState: "connecting",
    });
  },

  addUserMessage: (text) => {
    set((s) => ({
      messages: [...s.messages, { kind: "user", text, ts: Date.now() }],
      _lastSendTs: Date.now() / 1000, // Unix 秒，和 mtime 对齐
    }));
  },

  handleEvent: (envelope) => {
    const p = envelope.payload;
    switch (p.type) {
      case "cc_output_delta":
        set((s) => ({ pendingAssistant: s.pendingAssistant + p.text, isStreaming: true }));
        break;

      case "cc_thinking":
        set((s) => ({
          messages: [...s.messages, { kind: "thinking", text: p.text, ts: Date.now() }],
        }));
        break;

      case "tool_use_start":
        set((s) => ({
          messages: [...s.messages, { kind: "tool_use", tool: p.tool, args: p.args, ts: Date.now() }],
        }));
        break;

      case "cc_message_complete":
        get().markStreamComplete();
        // cc 完成后检测 docs/ 是否有新生成的文档
        void checkNewDoc(get()._lastSendTs);
        break;

      case "agent_error":
        set((s) => ({
          messages: [...s.messages, { kind: "error", message: p.message, ts: Date.now() }],
          isStreaming: false,
        }));
        break;

      case "session_ended":
        set({ wsState: "closed", isStreaming: false });
        break;

      // session_started / tool_use_end / spec_updated — no UI action in v1
      default:
        break;
    }
  },

  markStreamComplete: () => {
    const pending = get().pendingAssistant;
    if (!pending) return;
    set((s) => ({
      messages: [...s.messages, { kind: "assistant", text: pending, ts: Date.now() }],
      pendingAssistant: "",
      isStreaming: false,
    }));
  },

  setWsState: (state) => set({ wsState: state }),

  // 点开模板时调用：在 chat 加引导消息 + 预填充输入框
  triggerDocFill: (kind, label) => {
    const kindName = kind === "gameplay" ? "玩法设计" : kind === "prop" ? "物件需求" : "设计";
    const cmd = `/fill-gamedoc `;
    set((s) => ({
      messages: [
        ...s.messages,
        {
          kind: "hint" as const,
          text: `📄 ${label} 已在预览栏打开\n\n把源文件（group_doc HTML / IR JSON / 设计草稿）拖到附件区，或者直接在输入框里输入 /fill-gamedoc <源文件路径>，cc 会自动填充这份${kindName}文档。`,
          ts: Date.now(),
        },
      ],
      inputPrefill: cmd,
    }));
  },

  clearInputPrefill: () => set({ inputPrefill: null }),

  reset: () =>
    set({
      clientId: null,
      messages: [],
      wsState: "idle",
      pendingAssistant: "",
      isStreaming: false,
      attachedFiles: [],
      uploadingFiles: [],
    }),

  uploadFile: async (file: File) => {
    const { clientId } = get();
    if (!clientId) return;
    set((s) => ({ uploadingFiles: [...s.uploadingFiles, file.name] }));
    try {
      const uploaded = await api.uploadFile(clientId, file);
      set((s) => ({
        attachedFiles: [...s.attachedFiles, uploaded],
        uploadingFiles: s.uploadingFiles.filter((n) => n !== file.name),
      }));
    } catch (err) {
      set((s) => ({ uploadingFiles: s.uploadingFiles.filter((n) => n !== file.name) }));
      throw err;
    }
  },

  removeAttachedFile: async (file_id: string) => {
    const { clientId } = get();
    if (!clientId) return;
    await api.deleteFile(clientId, file_id);
    set((s) => ({ attachedFiles: s.attachedFiles.filter((f) => f.file_id !== file_id) }));
  },

  reloadAttachedFiles: async () => {
    const { clientId } = get();
    if (!clientId) return;
    const { files } = await api.listFiles(clientId);
    set({ attachedFiles: files });
  },
}));

// cc 完成后检测 docs/ 是否有比本次对话更新的文档，有则自动在预览栏显示
async function checkNewDoc(sendTs: number) {
  try {
    const res = await fetch("/api/docs");
    if (!res.ok) return;
    const list = await res.json() as Array<{ filename: string; url: string; kind: string; mtime: number }>;
    // 找比发送消息更新的文件（mtime > sendTs）
    const fresh = list.filter((d) => d.mtime > sendTs);
    if (fresh.length === 0) return;
    // 取最新的那个
    const newest = fresh[0];
    const kindLabel = newest.kind === "gameplay" ? "玩法设计文档" : newest.kind === "prop" ? "物件需求文档" : "设计文档";
    useEditorStore.getState().openDocTemplate(
      newest.url,
      `📄 ${kindLabel} · ${newest.filename}`,
    );
  } catch {
    // 静默失败，不影响 chat
  }
}
