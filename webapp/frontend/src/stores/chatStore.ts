// Chat client-side state：session、消息列表、WS 连接状态、流式累积。
// Server state 走 useChatSocket hook，store 只管 UI state。

import { create } from "zustand";
import { api } from "../api/client";
import type { AttachedFile, WsEnvelope } from "../api/chat-types";

export type ChatMessage =
  | { kind: "user"; text: string; ts: number }
  | { kind: "assistant"; text: string; cost_usd?: number; duration_ms?: number; ts: number }
  | { kind: "thinking"; text: string; ts: number }
  | { kind: "tool_use"; tool: string; args: unknown; ts: number }
  | { kind: "error"; message: string; ts: number };

export type WsState = "idle" | "connecting" | "open" | "closed";

type ChatState = {
  clientId: string | null;
  messages: ChatMessage[];
  wsState: WsState;
  pendingAssistant: string;
  isStreaming: boolean;
  attachedFiles: AttachedFile[];
  uploadingFiles: string[];

  initSession: () => Promise<void>;
  addUserMessage: (text: string) => void;
  handleEvent: (envelope: WsEnvelope) => void;
  markStreamComplete: () => void;
  setWsState: (state: WsState) => void;
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
