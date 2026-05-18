import type { SchemaLike } from "./labelUtils";
import { fieldLabel } from "./labelUtils";

type Schema = SchemaLike & { type?: string; minimum?: number; maximum?: number };

type Props = {
  schema: Schema;
  value: unknown;
  path: string;
  onChange: (path: string, value: unknown) => void;
  registerRef: (path: string, el: HTMLElement | null) => void;
};

export function NumberField({ schema, value, path, onChange, registerRef }: Props) {
  const { main, key } = fieldLabel(schema, path);
  const v = typeof value === "number" ? value : "";
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 4 }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{main}</span>
        <span style={{ fontSize: 10, color: "var(--text-faint)", fontFamily: "var(--mono)" }}>{key}</span>
      </label>
      <input
        ref={(el) => registerRef(path, el)}
        data-path={path}
        type="number"
        value={v}
        min={schema.minimum}
        max={schema.maximum}
        onChange={(e) => onChange(path, e.target.value === "" ? null : Number(e.target.value))}
        style={{
          width: "100%",
          padding: "6px 8px",
          fontSize: 13,
          border: "1px solid var(--border)",
          borderRadius: 3,
          background: "#fff",
        }}
      />
    </div>
  );
}

export function BoolField({ schema, value, path, onChange, registerRef }: Props) {
  const { main, key } = fieldLabel(schema, path);
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input
          ref={(el) => registerRef(path, el)}
          data-path={path}
          type="checkbox"
          checked={!!value}
          onChange={(e) => onChange(path, e.target.checked)}
        />
        <span style={{ fontSize: 13, fontWeight: 600 }}>{main}</span>
        <span style={{ fontSize: 10, color: "var(--text-faint)", fontFamily: "var(--mono)" }}>{key}</span>
      </label>
    </div>
  );
}
