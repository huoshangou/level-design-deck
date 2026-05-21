import type { SchemaLike } from "./labelUtils";
import { fieldLabel } from "./labelUtils";
import Field from "./Field";

type Schema = SchemaLike & {
  type?: string;
  items?: SchemaLike & { type?: string };
};

type Props = {
  schema: Schema;
  value: unknown;
  path: string;
  onChange: (path: string, value: unknown) => void;
  registerRef: (path: string, el: HTMLElement | null) => void;
};

export default function ArrayField({ schema, value, path, onChange, registerRef }: Props) {
  const { main, key } = fieldLabel(schema, path);
  const arr = Array.isArray(value) ? value : [];
  const itemSchema = schema.items ?? {};
  const isStringItems = itemSchema.type === "string" && !itemSchema.title;

  function setItem(i: number, v: unknown) {
    const next = arr.slice();
    next[i] = v;
    onChange(path, next);
  }
  function removeItem(i: number) {
    const next = arr.slice();
    next.splice(i, 1);
    onChange(path, next);
  }
  function addItem() {
    const blank = itemSchema.type === "object" ? {} : itemSchema.type === "array" ? [] : "";
    onChange(path, [...arr, blank]);
  }

  return (
    <fieldset
      ref={(el) => registerRef(path, el)}
      data-path={path}
      style={{
        marginBottom: 16,
        border: "1px solid var(--border)",
        borderRadius: 3,
        padding: "10px 14px",
        background: "var(--section-bg)",
      }}
    >
      <legend style={{ padding: "0 6px", fontSize: 12, fontWeight: 600 }}>
        {main}
        <span style={{ fontSize: 10, color: "var(--text-faint)", fontFamily: "var(--mono)", marginLeft: 6 }}>
          {key}[{arr.length}]
        </span>
      </legend>
      {arr.map((item, i) => (
        <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 6 }}>
          <span style={{ fontSize: 10, color: "var(--text-faint)", fontFamily: "var(--mono)", marginTop: 8, minWidth: 24 }}>
            [{i}]
          </span>
          <div style={{ flex: 1 }}>
            {isStringItems ? (
              <input
                type="text"
                value={typeof item === "string" ? item : ""}
                onChange={(e) => setItem(i, e.target.value)}
                style={{
                  width: "100%",
                  padding: "4px 8px",
                  fontSize: 13,
                  border: "1px solid var(--border)",
                  borderRadius: 3,
                }}
              />
            ) : (
              <Field
                schema={itemSchema}
                value={item}
                path={`${path}[${i}]`}
                onChange={onChange}
                registerRef={registerRef}
              />
            )}
          </div>
          <button
            type="button"
            onClick={() => removeItem(i)}
            style={{
              padding: "2px 6px",
              fontSize: 10,
              border: "1px solid var(--border)",
              background: "#fff",
              borderRadius: 2,
              color: "var(--error)",
            }}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addItem}
        style={{
          padding: "4px 10px",
          fontSize: 11,
          border: "1px dashed var(--border)",
          background: "transparent",
          borderRadius: 2,
          color: "var(--text-dim)",
          marginTop: 4,
        }}
      >
        + 添加
      </button>
    </fieldset>
  );
}
