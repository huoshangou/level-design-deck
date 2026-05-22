// WS envelope + 9 种 event payload 类型定义。
// 与 backend/agent/events.py 对齐，按 payload.type 判别。

// ── Event payloads ──────────────────────────────────────────────────────────

export type SessionStartedPayload = {
  type: "session_started";
  client_id: string;
  cc_session_id: string;
};

export type CcOutputDeltaPayload = {
  type: "cc_output_delta";
  text: string;
  message_id: string;
};

export type CcThinkingPayload = {
  type: "cc_thinking";
  text: string;
};

export type ToolUseStartPayload = {
  type: "tool_use_start";
  tool: string;
  args: Record<string, unknown>;
  tool_use_id: string;
};

export type ToolUseEndPayload = {
  type: "tool_use_end";
  tool: string;
  tool_use_id: string;
  ok: boolean;
  summary: string;
};

export type CcMessageCompletePayload = {
  type: "cc_message_complete";
  text: string;
  role: string;
  cost_usd: number;
  duration_ms: number;
  cc_session_id: string;
};

export type SpecUpdatedPayload = {
  type: "spec_updated";
  spec_id: string;
  mtime: number;
  source: string;
};

export type AgentErrorPayload = {
  type: "agent_error";
  code: string;
  message: string;
  recoverable: boolean;
};

export type SessionEndedPayload = {
  type: "session_ended";
  reason: string;
};

export type CcInterruptedPayload = {
  type: "cc_interrupted";
  cc_session_id: string | null;
};

export type EventPayload =
  | SessionStartedPayload
  | CcOutputDeltaPayload
  | CcThinkingPayload
  | ToolUseStartPayload
  | ToolUseEndPayload
  | CcMessageCompletePayload
  | SpecUpdatedPayload
  | AgentErrorPayload
  | SessionEndedPayload
  | CcInterruptedPayload;

// ── WS envelope ─────────────────────────────────────────────────────────────

export type WsEnvelope = {
  type: string;
  ts: string;
  client_id: string;
  payload: EventPayload;
};

// ── REST response types ──────────────────────────────────────────────────────

export type SessionRecord = {
  client_id: string;
  namespace: string;
  started_at: string;
  cc_session_id: string;
};

export type MessageQueued = {
  queued: true;
};

export type AttachedFile = {
  file_id: string;
  original_name: string;
  stored_path: string;
  text_path: string | null;
  size_bytes: number;
  kind: "text" | "docx" | "pptx" | "xlsx" | "html" | "htm" | "binary";
  uploaded_at: number;
};
