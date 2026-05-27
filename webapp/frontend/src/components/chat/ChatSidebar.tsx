// 右侧 360px Chat 侧边栏：header + 消息列表 + 附件区 + 输入区。
import { useEffect, useRef, useState } from "react";
import { useChatStore } from "../../stores/chatStore";
import { useChatSocket } from "../../hooks/useChatSocket";
import { api, type CcHistoryEntry } from "../../api/client";
import MessageBubble from "./MessageBubble";
import AttachmentArea from "./AttachmentArea";
import ProfileButton from "./ProfileButton";

const WS_DOT: Record<string, string> = {
  idle: "var(--text-faint)",
  connecting: "var(--review)",
  open: "var(--success)",
  closed: "var(--error)",
};

export default function ChatSidebar() {
  const {
    clientId,
    messages,
    wsState,
    pendingAssistant,
    isStreaming,
    awaitingResponse,
    awaitingStartTs,
    lastActivityTs,
    lastActivityLabel,
    interruptRequested,
    inputPrefill,
    initSession,
    loadHistorySession,
    addUserMessage,
    markSendFailed,
    requestInterrupt,
    clearInputPrefill,
    reset,
    uploadFile,
  } = useChatStore();

  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState<CcHistoryEntry[] | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const historyBtnRef = useRef<HTMLButtonElement>(null);
  const [historyAnchor, setHistoryAnchor] = useState<{ top: number; right: number } | null>(null);

  async function openHistory() {
    // 锁定下拉锚点位置（脱离 sidebar overflow:hidden）
    const rect = historyBtnRef.current?.getBoundingClientRect();
    if (rect) {
      setHistoryAnchor({
        top: rect.bottom + 4,
        right: window.innerWidth - rect.right,
      });
    }
    setHistoryOpen(true);
    if (!historyList) {
      setHistoryLoading(true);
      try {
        const list = await api.listCcHistory(30);
        setHistoryList(list);
      } catch (e) {
        alert(`加载历史失败：${String(e)}`);
      } finally {
        setHistoryLoading(false);
      }
    }
  }

  async function pickHistory(cc_session_id: string) {
    setHistoryOpen(false);
    try {
      await loadHistorySession(cc_session_id);
    } catch (e) {
      alert(`恢复失败：${String(e)}`);
    }
  }

  function fmtRelTime(ts: number) {
    const sec = (Date.now() / 1000 - ts);
    if (sec < 60) return "刚才";
    if (sec < 3600) return `${Math.floor(sec / 60)}分钟前`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}小时前`;
    if (sec < 86400 * 7) return `${Math.floor(sec / 86400)}天前`;
    return new Date(ts * 1000).toLocaleDateString("zh-CN");
  }

  useChatSocket(clientId);

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sidebarDragging, setSidebarDragging] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingAssistant]);

  // 1Hz tick：等待响应时驱动占位气泡显示流逝秒数
  const [, setNowTick] = useState(0);
  useEffect(() => {
    if (!awaitingResponse) return;
    const id = setInterval(() => setNowTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [awaitingResponse]);
  const elapsedSec = awaitingStartTs ? Math.max(0, Math.floor((Date.now() - awaitingStartTs) / 1000)) : 0;
  const sinceLastActivitySec = lastActivityTs ? Math.max(0, Math.floor((Date.now() - lastActivityTs) / 1000)) : null;

  // 消费预填充指令（点开模板时触发）
  useEffect(() => {
    if (!inputPrefill) return;
    setInput(inputPrefill);
    clearInputPrefill();
    inputRef.current?.focus();
  }, [inputPrefill, clearInputPrefill]);

  // 页面加载时自动建 session（避免新用户卡在「+ 新建」按钮上）
  useEffect(() => {
    if (!clientId) {
      void initSession();
    }
  }, []);

  async function handleNewSession() {
    reset();
    await initSession();
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || !clientId || isStreaming || awaitingResponse || busy) return;
    setBusy(true);
    try {
      // WS 没就绪时等一会：常发生在页面刚加载 / React strict mode 重连
      if (wsState !== "open") {
        for (let i = 0; i < 30; i++) {  // 最多等 3s
          await new Promise((r) => setTimeout(r, 100));
          if (useChatStore.getState().wsState === "open") break;
        }
        if (useChatStore.getState().wsState !== "open") {
          alert("WebSocket 未连接，请稍候或点 + 新建 重试");
          return;
        }
      }
      addUserMessage(text);
      setInput("");
      try {
        await api.sendMessage(clientId, text);
      } catch (e) {
        // 409 = backend _ws_connected 没认到 → 多半是 StrictMode race 残留 / WS 刚断
        // sleep 500ms 让 useChatSocket 重连后端 ws handler 重新注册，再试一次
        if (String(e).includes("409")) {
          await new Promise((r) => setTimeout(r, 500));
          try {
            await api.sendMessage(clientId, text);
          } catch (e2) {
            markSendFailed(String(e2));
            throw e2;
          }
        } else {
          markSendFailed(String(e));
          throw e;
        }
      }
    } catch (e) {
      alert(`发送失败：${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    } else if (e.key === "Escape" && (isStreaming || awaitingResponse)) {
      e.preventDefault();
      requestInterrupt();
    }
  }

  const disabled = isStreaming || awaitingResponse || busy || !clientId;

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
        background: sidebarDragging ? "var(--accent-bg)" : "var(--bg)",
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
        <div style={{ display: "flex", gap: 4 }}>
          <ProfileButton />
          <button
            ref={historyBtnRef}
            onClick={() => void openHistory()}
            style={{
              padding: "3px 8px",
              fontSize: 11,
              border: "1px solid var(--border)",
              borderRadius: 3,
              background: "var(--panel)",
              color: "var(--text)",
              cursor: "pointer",
            }}
            title="加载历史会话"
          >
            📜 历史
          </button>
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
          {historyOpen && historyAnchor && (
            <>
              <div
                onClick={() => setHistoryOpen(false)}
                style={{ position: "fixed", inset: 0, zIndex: 50 }}
              />
              <div
                style={{
                  position: "fixed",
                  top: historyAnchor.top,
                  right: historyAnchor.right,
                  zIndex: 51,
                  width: 360,
                  maxHeight: 480,
                  overflowY: "auto",
                  background: "var(--panel)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  boxShadow: "var(--shadow)",
                  fontSize: 12,
                }}
              >
                <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-dim)", fontWeight: 600, fontSize: 11 }}>
                  最近 30 个历史会话
                </div>
                {historyLoading && (
                  <div style={{ padding: 16, textAlign: "center", color: "var(--text-faint)" }}>加载中…</div>
                )}
                {!historyLoading && historyList && historyList.length === 0 && (
                  <div style={{ padding: 16, textAlign: "center", color: "var(--text-faint)" }}>无历史</div>
                )}
                {!historyLoading && historyList?.map((h) => (
                  <button
                    key={h.cc_session_id}
                    onClick={() => void pickHistory(h.cc_session_id)}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      padding: "8px 12px",
                      border: "none",
                      borderBottom: "1px solid var(--border-faint)",
                      background: "transparent",
                      cursor: "pointer",
                      color: "var(--text)",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
                      <span style={{ color: "var(--text-dim)", fontSize: 10, fontFamily: "var(--mono)" }}>
                        {h.cc_session_id.slice(0, 8)}
                      </span>
                      <span style={{ color: "var(--text-faint)", fontSize: 10 }}>
                        {fmtRelTime(h.mtime)} · {h.user_turns} 轮
                      </span>
                    </div>
                    <div style={{ marginTop: 3, color: "var(--text)", lineHeight: 1.4, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                      {h.first_user || <em style={{ color: "var(--text-faint)" }}>（无预览）</em>}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
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
        {/* awaiting 占位：消息已发出但还没有 streaming 文本时显示 */}
        {awaitingResponse && !pendingAssistant && (
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 8 }}>
            <div
              style={{
                maxWidth: "85%",
                padding: "8px 12px",
                borderRadius: "12px 12px 12px 2px",
                background: "var(--panel)",
                border: "1px dashed var(--border)",
                fontSize: 12,
                lineHeight: 1.5,
                color: "var(--text-faint)",
                fontFamily: "var(--sans)",
              }}
            >
              <span style={{ marginRight: 4 }}>⏳</span>
              cc 处理中… {elapsedSec}s
              {lastActivityLabel && sinceLastActivitySec !== null && (
                <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-dim)" }}>
                  最近: {lastActivityLabel} · {sinceLastActivitySec}s 前
                </div>
              )}
              {elapsedSec >= 60 && (
                <div style={{ marginTop: 4, fontSize: 11, color: "var(--review)" }}>
                  ⚠️ 已等待 {elapsedSec}s，cc 可能卡住，可以点「停止」终止 turn
                </div>
              )}
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
            ref={inputRef}
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
          {(isStreaming || awaitingResponse) ? (
            <button
              onClick={() => requestInterrupt()}
              disabled={interruptRequested}
              title={interruptRequested ? "已请求停止，等 cc 收尾" : "停止当前 cc turn（Esc）"}
              style={{
                padding: "6px 12px",
                fontSize: 12,
                border: "none",
                borderRadius: 4,
                background: interruptRequested ? "var(--border)" : "var(--error)",
                color: interruptRequested ? "var(--text-faint)" : "#fff",
                cursor: interruptRequested ? "wait" : "pointer",
                flexShrink: 0,
                alignSelf: "stretch",
              }}
            >
              {interruptRequested ? "⏸ 收尾..." : "⏹ 停止"}
            </button>
          ) : (
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
              发送
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
