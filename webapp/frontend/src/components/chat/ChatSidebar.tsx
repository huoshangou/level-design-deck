// 右侧 360px Chat 侧边栏：header + 消息列表 + 附件区 + 输入区。
import { useEffect, useRef, useState } from "react";
import { useChatStore } from "../../stores/chatStore";
import { useChatSocket } from "../../hooks/useChatSocket";
import { api } from "../../api/client";
import MessageBubble from "./MessageBubble";
import AttachmentArea from "./AttachmentArea";

const WS_DOT: Record<string, string> = {
  idle: "var(--text-faint)",
  connecting: "var(--review)",
  open: "#22c55e",
  closed: "var(--error)",
};

export default function ChatSidebar() {
  const {
    clientId,
    messages,
    wsState,
    pendingAssistant,
    isStreaming,
    initSession,
    addUserMessage,
    reset,
    uploadFile,
  } = useChatStore();

  useChatSocket(clientId);

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sidebarDragging, setSidebarDragging] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 自动滚到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingAssistant]);

  async function handleNewSession() {
    reset();
    await initSession();
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || !clientId || isStreaming || busy) return;
    setBusy(true);
    try {
      addUserMessage(text);
      setInput("");
      await api.sendMessage(clientId, text);
    } catch (e) {
      // 错误已由 WS agent_error 事件承接；REST 失败就简单 alert
      alert(`发送失败：${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  const disabled = isStreaming || busy || !clientId;

  // Sidebar-level drag forwarding — when user drags over message area,
  // we still want the AttachmentArea dropzone to receive it.
  function onSidebarDragOver(e: React.DragEvent) {
    e.preventDefault();
    setSidebarDragging(true);
  }
  function onSidebarDragLeave(e: React.DragEvent) {
    // only clear when leaving the aside itself (not a child)
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setSidebarDragging(false);
    }
  }
  async function onSidebarDrop(e: React.DragEvent) {
    e.preventDefault();
    setSidebarDragging(false);
    if (!clientId || !e.dataTransfer.files.length) return;
    for (const f of Array.from(e.dataTransfer.files)) {
      try { await uploadFile(f); }
      catch (err) { alert(`上传失败：${f.name}\n${String(err)}`); }
    }
  }

  return (
    <aside
      onDragOver={onSidebarDragOver}
      onDragLeave={onSidebarDragLeave}
      onDrop={(e) => void onSidebarDrop(e)}
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderLeft: "1px solid var(--border)",
        background: sidebarDragging ? "rgba(99,102,241,0.04)" : "var(--bg)",
        overflow: "hidden",
        transition: "background 0.15s",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          borderBottom: "1px solid var(--border)",
          background: "var(--panel)",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: WS_DOT[wsState] ?? "var(--text-faint)",
            display: "inline-block",
            flexShrink: 0,
          }}
          title={`WS: ${wsState}`}
        />
        <h2 style={{ margin: 0, fontSize: 12, fontWeight: 600, color: "var(--text-dim)", letterSpacing: 1, flex: 1 }}>
          Chat
          {clientId && (
            <span style={{ fontFamily: "var(--mono)", fontWeight: 400, marginLeft: 6, fontSize: 10, color: "var(--text-faint)" }}>
              {clientId.slice(0, 8)}…
            </span>
          )}
        </h2>
        <button
          onClick={() => void handleNewSession()}
          style={{
            padding: "3px 8px",
            fontSize: 11,
            border: "1px solid var(--border)",
            borderRadius: 3,
            background: "var(--panel)",
            color: "var(--text)",
            cursor: "pointer",
          }}
          title="新建 session"
        >
          + 新建
        </button>
      </div>

      {/* Message list */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 12px 4px",
        }}
      >
        {messages.length === 0 && !pendingAssistant && (
          <p style={{ fontSize: 12, color: "var(--text-faint)", textAlign: "center", marginTop: 40 }}>
            {clientId ? "发条消息开始对话" : "点「+ 新建」创建 session"}
          </p>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {/* 正在流式输出的部分内容 */}
        {pendingAssistant && (
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 8 }}>
            <div
              style={{
                maxWidth: "85%",
                padding: "8px 12px",
                borderRadius: "12px 12px 12px 2px",
                background: "var(--panel)",
                border: "1px solid var(--border)",
                fontSize: 13,
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {pendingAssistant}
              <span style={{ display: "inline-block", width: 6, height: 12, background: "var(--accent)", marginLeft: 2, verticalAlign: "text-bottom", animation: "blink 1s step-end infinite" }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Attachment area */}
      <AttachmentArea clientId={clientId} />

      {/* Input area */}
      <div
        style={{
          padding: "8px 12px",
          background: "var(--panel)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={clientId ? "输入消息，Enter 发送，Shift+Enter 换行" : "先新建 session"}
            disabled={!clientId}
            rows={2}
            style={{
              flex: 1,
              resize: "none",
              padding: "6px 8px",
              fontSize: 12,
              border: "1px solid var(--border)",
              borderRadius: 4,
              background: clientId ? "#fff" : "var(--section-bg)",
              color: "var(--text)",
              fontFamily: "var(--sans)",
              lineHeight: 1.5,
            }}
          />
          <button
            onClick={() => void handleSend()}
            disabled={disabled || !input.trim()}
            style={{
              padding: "6px 12px",
              fontSize: 12,
              border: "none",
              borderRadius: 4,
              background: disabled || !input.trim() ? "var(--border)" : "var(--accent)",
              color: disabled || !input.trim() ? "var(--text-faint)" : "#fff",
              cursor: disabled || !input.trim() ? "not-allowed" : "pointer",
              flexShrink: 0,
              alignSelf: "stretch",
            }}
          >
            {isStreaming ? "…" : "发送"}
          </button>
        </div>
      </div>
    </aside>
  );
}
