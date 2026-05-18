import type { SchemaLike } from "./labelUtils";
import { fieldLabel } from "./labelUtils";

type Schema = SchemaLike & {
  type?: string;
  enum?: string[];
  minLength?: number;
  pattern?: string;
};

type Props = {
  schema: Schema;
  value: unknown;
  path: string;
  onChange: (path: string, value: unknown) => void;
  registerRef: (path: string, el: HTMLElement | null) => void;
};

export default function StringField({ schema, value, path, onChange, registerRef }: Props) {
  const { main, key } = fieldLabel(schema, path);
  const v = typeof value === "string" ? value : "";
  const longText = (schema.minLength ?? 0) >= 10 || v.length > 60;

  const commonProps = {
    "data-path": path,
    value: v,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      onChange(path, e.target.value),
  } as const;

  return (
    <div style={ROW}>
      <label style={LABEL}>
        <span style={MAIN}>{main}</span>
        <span style={SUB}>{key}</span>
        {schema.description && <span style={HINT}>{schema.description}</span>}
      </label>
      {schema.enum ? (
        <select {...commonProps} ref={(el) => registerRef(path, el)} style={INPUT}>
          <option value="">— 选择 —</option>
          {schema.enum.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      ) : longText ? (
        <textarea
          {...commonProps}
          ref={(el) => registerRef(path, el)}
          rows={Math.min(8, Math.max(3, Math.ceil(v.length / 60)))}
          style={{ ...INPUT, fontFamily: "var(--mono)", resize: "vertical" }}
        />
      ) : (
        <input {...commonProps} ref={(el) => registerRef(path, el)} type="text" style={INPUT} />
      )}
      {schema.pattern && (
        <small style={HINT_BELOW}>pattern: <code>{schema.pattern}</code></small>
      )}
    </div>
  );
}

const ROW = { marginBottom: 12 } as const;
const LABEL = { display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4, flexWrap: "wrap" as const };
const MAIN = { fontSize: 13, color: "var(--text)", fontWeight: 600 } as const;
const SUB = { fontSize: 10, color: "var(--text-faint)", fontFamily: "var(--mono)" } as const;
const HINT = { fontSize: 11, color: "var(--text-faint)" } as const;
const HINT_BELOW = { fontSize: 10, color: "var(--text-faint)", marginTop: 2, display: "block" } as const;
const INPUT = {
  width: "100%",
  padding: "6px 8px",
  fontSize: 13,
  border: "1px solid var(--border)",
  borderRadius: 3,
  background: "#fff",
  boxSizing: "border-box" as const,
};
