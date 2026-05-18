import type { Alert } from "../api/types";

type Props = {
  alerts: Alert[];
  isLoading: boolean;
  onJump: (path: string) => void;
};

const COLOR: Record<Alert["level"], string> = {
  ERROR: "var(--error)",
  REVIEW: "var(--review)",
  MISSING: "var(--review)",
  EXTRA: "var(--text-dim)",
  INFO: "var(--accent)",
};

const ORDER: Record<Alert["level"], number> = {
  ERROR: 0,
  REVIEW: 1,
  MISSING: 2,
  EXTRA: 3,
  INFO: 4,
};

export default function AlertsSidebar({ alerts, isLoading, onJump }: Props) {
  const sorted = [...alerts].sort((a, b) => ORDER[a.level] - ORDER[b.level]);
  const stats = alerts.reduce<Record<string, number>>((acc, a) => {
    acc[a.level] = (acc[a.level] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <aside
      style={{
        width: 320,
        flex: "0 0 320px",
        borderRight: "1px solid var(--border)",
        background: "var(--panel)",
        overflow: "auto",
        padding: "12px 16px",
      }}
    >
      <h2 style={{ fontSize: 12, margin: "0 0 12px", color: "var(--text-dim)", letterSpacing: 1 }}>
        告警 {isLoading && "…"}
      </h2>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12, fontSize: 11 }}>
        {(["ERROR", "REVIEW", "MISSING", "EXTRA"] as const).map((k) => (
          <span
            key={k}
            style={{
              padding: "2px 6px",
              borderRadius: 2,
              background: stats[k] ? COLOR[k] : "transparent",
              color: stats[k] ? "#fff" : "var(--text-faint)",
              border: stats[k] ? "none" : "1px dashed var(--border)",
            }}
          >
            {k} {stats[k] ?? 0}
          </span>
        ))}
      </div>
      {sorted.length === 0 && !isLoading && (
        <p style={{ fontSize: 12, color: "var(--text-faint)" }}>无告警 ✓</p>
      )}
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {sorted.map((a, i) => (
          <li
            key={i}
            onClick={() => a.field_path && onJump(a.field_path)}
            style={{
              padding: "8px 10px",
              marginBottom: 4,
              borderRadius: 3,
              border: "1px solid var(--border)",
              cursor: a.field_path ? "pointer" : "default",
              background: "#fff",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-bg)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#fff")}
          >
            <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
              <span style={{ fontSize: 10, color: "#fff", padding: "1px 5px", background: COLOR[a.level], borderRadius: 2 }}>
                {a.level}
              </span>
              <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{a.source}</span>
              <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{a.rule}</span>
            </div>
            {a.field_path && (
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--accent)", marginBottom: 2 }}>
                {a.field_path}
              </div>
            )}
            <div style={{ fontSize: 12, color: "var(--text)" }}>{a.msg}</div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
