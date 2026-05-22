// Chat client-side state：session、消息列表、WS 连接状态、流式累积。
// Server state 走 useChatSocket hook，store 只管 UI state。

import { create } from "zustand";
import { api } from "../api/client";
import { useEditorStore } from "./editorStore";
import { sendInterrupt } from "../hooks/useChatSocket";
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
  awaitingResponse: boolean;       // 发出消息后，cc 完整 turn 未结束之前为 true
  awaitingStartTs: number | null;  // awaitingResponse 起始时刻（ms），用来算耗时
  // cc 正在 awaiting 时，最近一次"有动静"是什么时间 / 干啥（thinking / tool / streaming），
  // 用来给 awaiting 占位气泡加 "5s 前 🔧 Read" 这种活体感
  lastActivityTs: number | null;
  lastActivityLabel: string | null;
  interruptRequested: boolean;     // 用户已经按过 stop、等后端 ack 中
  attachedFiles: AttachedFile[];
  uploadingFiles: string[];
  _lastSendTs: number;
  inputPrefill: string | null; // 预填充输入框内容，消费后置 null

  initSession: () => Promise<void>;
  loadHistorySession: (cc_session_id: string) => Promise<void>;
  addUserMessage: (text: string) => void;
  markSendFailed: (errMsg: string) => void;
  handleEvent: (envelope: WsEnvelope) => void;
  markStreamComplete: () => void;
  setWsState: (state: WsState) => void;
  requestInterrupt: () => void;
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
  awaitingResponse: false,
  awaitingStartTs: null,
  lastActivityTs: null,
  lastActivityLabel: null,
  interruptRequested: false,
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
      awaitingResponse: false,
      awaitingStartTs: null,
      lastActivityTs: null,
      lastActivityLabel: null,
      interruptRequested: false,
      wsState: "connecting",
    });
  },

  loadHistorySession: async (cc_session_id: string) => {
    // 1. 并行拉消息 + 产物文档
    const [historyMsgs, generatedDocs] = await Promise.all([
      api.getCcHistoryMessages(cc_session_id),
      api.getCcHistoryGeneratedDocs(cc_session_id).catch(() => []),
    ]);
    // 2. 创建新 webapp session，cc_session_id 复用旧的（下次发消息 cc CLI 会 --resume）
    const record = await api.createSession({ cc_session_id });
    const now = Date.now();
    const messages: ChatMessage[] = historyMsgs
      .map((m): ChatMessage | null => {
        const ts = m.ts ?? now;
        if (m.kind === "user") return { kind: "user", text: m.text, ts };
        if (m.kind === "assistant") return { kind: "assistant", text: m.text, ts };
        if (m.kind === "thinking") return { kind: "thinking", text: m.text, ts };
        if (m.kind === "tool_use") return { kind: "tool_use", tool: m.tool ?? "?", args: m.text, ts };
        return null;
      })
      .filter((x): x is ChatMessage => x !== null);

    // 3. 自动打开最新的、还存在的产物文档
    const aliveDocs = generatedDocs.filter((d) => d.exists);
    const newest = aliveDocs[0]; // backend 已按 last_touched 倒序
    let hintText = `📜 已恢复历史会话（${historyMsgs.length} 条消息），继续输入即可接力对话`;
    if (newest) {
      hintText += `\n📄 已在预览栏打开当时生成的：${newest.filename}`;
      useEditorStore.getState().openDocTemplate(newest.url, `📄 ${newest.filename}`);
    } else if (generatedDocs.length > 0) {
      hintText += `\n⚠️ 当时生成过 ${generatedDocs.length} 个文档，但当前 docs/ 下已找不到`;
    }

    set({
      clientId: record.client_id,
      messages: [
        { kind: "hint" as const, text: hintText, ts: now },
        ...messages,
      ],
      pendingAssistant: "",
      isStreaming: false,
      awaitingResponse: false,
      awaitingStartTs: null,
      lastActivityTs: null,
      lastActivityLabel: null,
      interruptRequested: false,
      wsState: "connecting",
    });
  },

  addUserMessage: (text) => {
    const now = Date.now();
    set((s) => ({
      messages: [...s.messages, { kind: "user", text, ts: now }],
      _lastSendTs: now / 1000, // Unix 秒，和 mtime 对齐
      awaitingResponse: true,
      awaitingStartTs: now,
      lastActivityTs: null,
      lastActivityLabel: null,
      interruptRequested: false,
    }));
  },

  // 发送 POST 失败时回滚：清掉"处理中"状态，并把错误塞进消息流
  markSendFailed: (errMsg: string) => {
    set((s) => ({
      awaitingResponse: false,
      awaitingStartTs: null,
      lastActivityTs: null,
      lastActivityLabel: null,
      interruptRequested: false,
      messages: [...s.messages, { kind: "error", message: `发送失败：${errMsg}`, ts: Date.now() }],
    }));
  },

  // 用户按 Stop 按钮：立即给后端推 interrupt 帧 + 加 hint + 锁按钮
  // 真正的"已停止"由后端回的 cc_interrupted 事件触发（见 handleEvent）
  requestInterrupt: () => {
    const { awaitingResponse, interruptRequested } = get();
    if (!awaitingResponse || interruptRequested) return;
    const ok = sendInterrupt();
    if (!ok) {
      // WS 没开就直接前端 mark 停 —— 不让用户卡在锁定状态
      set({
        awaitingResponse: false,
        awaitingStartTs: null,
        lastActivityTs: null,
        lastActivityLabel: null,
        interruptRequested: false,
        messages: [...get().messages, { kind: "hint", text: "🛑 WS 未连接，已就地停止（cc 子进程可能还在跑，下条消息会用新进程）", ts: Date.now() }],
      });
      return;
    }
    set((s) => ({
      interruptRequested: true,
      messages: [...s.messages, { kind: "hint", text: "🛑 已请求停止，等 cc 收尾...", ts: Date.now() }],
    }));
  },

  handleEvent: (envelope) => {
    const p = envelope.payload;
    const now = Date.now();
    switch (p.type) {
      case "cc_output_delta":
        set((s) => ({
          pendingAssistant: s.pendingAssistant + p.text,
          isStreaming: true,
          lastActivityTs: now,
          lastActivityLabel: "✍️ 输出中",
        }));
        break;

      case "cc_thinking":
        set((s) => ({
          messages: [...s.messages, { kind: "thinking", text: p.text, ts: now }],
          lastActivityTs: now,
          lastActivityLabel: "💭 思考",
        }));
        break;

      case "tool_use_start":
        set((s) => ({
          messages: [...s.messages, { kind: "tool_use", tool: p.tool, args: p.args, ts: now }],
          lastActivityTs: now,
          lastActivityLabel: `🔧 ${p.tool}`,
        }));
        break;

      case "cc_message_complete":
        get().markStreamComplete();
        set({
          awaitingResponse: false,
          awaitingStartTs: null,
          lastActivityTs: null,
          lastActivityLabel: null,
          interruptRequested: false,
        });
        // cc 完成后检测 docs/ 是否有新生成的文档
        void checkNewDoc(get()._lastSendTs);
        break;

      case "cc_interrupted":
        // 用户主动 stop 的受控终止 —— flush 半截输出 + 加"已停止"hint，不当 error 报
        get().markStreamComplete();
        set((s) => ({
          messages: [...s.messages, { kind: "hint", text: "✋ 已停止", ts: now }],
          awaitingResponse: false,
          awaitingStartTs: null,
          lastActivityTs: null,
          lastActivityLabel: null,
          interruptRequested: false,
        }));
        break;

      case "agent_error":
        set((s) => ({
          messages: [...s.messages, { kind: "error", message: p.message, ts: now }],
          isStreaming: false,
          awaitingResponse: false,
          awaitingStartTs: null,
          lastActivityTs: null,
          lastActivityLabel: null,
          interruptRequested: false,
        }));
        break;

      case "session_ended":
        set({
          wsState: "closed",
          isStreaming: false,
          awaitingResponse: false,
          awaitingStartTs: null,
          lastActivityTs: null,
          lastActivityLabel: null,
          interruptRequested: false,
        });
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
      awaitingResponse: false,
      awaitingStartTs: null,
      lastActivityTs: null,
      lastActivityLabel: null,
      interruptRequested: false,
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
