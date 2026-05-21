// 按 ChatMessage.kind 渲染对应样式气泡。
import type { ChatMessage } from "../../stores/chatStore";

type Props = { msg: ChatMessage };

function fmtTime(ts: number) {
  return new Date(ts).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function MessageBubble({ msg }: Props) {
  if (msg.kind === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <div
          style={{
            maxWidth: "80%",
            padding: "8px 12px",
            borderRadius: "12px 12px 2px 12px",
            background: "var(--accent)",
            color: "#fff",
            fontSize: 13,
            lineHeight: 1.5,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {msg.text}
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", marginTop: 2, textAlign: "right" }}>
            {fmtTime(msg.ts)}
          </div>
        </div>
      </div>
    );
  }

  if (msg.kind === "assistant") {
    return (
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
          {msg.text}
          <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 4, display: "flex", gap: 8 }}>
            <span>{fmtTime(msg.ts)}</span>
            {msg.cost_usd !== undefined && <span>${msg.cost_usd.toFixed(4)}</span>}
            {msg.duration_ms !== undefined && <span>{msg.duration_ms}ms</span>}
          </div>
        </div>
      </div>
    );
  }

  if (msg.kind === "thinking") {
    return (
      <div style={{ marginBottom: 6 }}>
        <details>
          <summary
            style={{
              fontSize: 11,
              color: "var(--text-faint)",
              cursor: "pointer",
              userSelect: "none",
              listStyle: "none",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            💭 思考
          </summary>
          <div
            style={{
              marginTop: 4,
              padding: "6px 10px",
              background: "var(--section-bg)",
              borderRadius: 4,
              fontSize: 12,
              color: "var(--text-dim)",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {msg.text}
          </div>
        </details>
      </div>
    );
  }

  if (msg.kind === "tool_use") {
    return (
      <div style={{ marginBottom: 6 }}>
        <details>
          <summary
            style={{
              fontSize: 11,
              color: "var(--text)",
              cursor: "pointer",
              userSelect: "none",
              listStyle: "none",
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "4px 8px",
              background: "var(--review-bg)",
              border: "1px solid var(--review)",
              borderRadius: 4,
            }}
          >
            🔧 Tool: {msg.tool}
          </summary>
          <pre
            style={{
              margin: "4px 0 0",
              padding: "6px 10px",
              background: "var(--review-bg)",
              borderRadius: "0 0 4px 4px",
              fontSize: 11,
              fontFamily: "var(--mono)",
              color: "var(--text-dim)",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {JSON.stringify(msg.args, null, 2)}
          </pre>
        </details>
      </div>
    );
  }

  if (msg.kind === "error") {
    return (
      <div
        style={{
          marginBottom: 6,
          padding: "8px 10px",
          border: "1px solid var(--error)",
          borderRadius: 4,
          background: "var(--error-bg)",
          fontSize: 12,
          color: "var(--error)",
        }}
      >
        ⚠ {msg.message}
      </div>
    );
  }

  if (msg.kind === "hint") {
    return (
      <div
        style={{
          marginBottom: 8,
          padding: "10px 12px",
          border: "1px solid var(--accent)",
          borderRadius: 6,
          background: "var(--accent-bg)",
          fontSize: 12,
          color: "var(--text)",
          lineHeight: 1.6,
          whiteSpace: "pre-line",
        }}
      >
        {msg.text}
      </div>
    );
  }

  return null;
}
