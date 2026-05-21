import type { SchemaLike } from "./labelUtils";
import { fieldLabel } from "./labelUtils";
import Field from "./Field";

type Schema = SchemaLike & {
  type?: string;
  properties?: Record<string, SchemaLike>;
  required?: string[];
};

type Props = {
  schema: Schema;
  value: unknown;
  path: string;
  onChange: (path: string, value: unknown) => void;
  registerRef: (path: string, el: HTMLElement | null) => void;
};

export default function ObjectField({ schema, value, path, onChange, registerRef }: Props) {
  const { main, key } = fieldLabel(schema, path);
  const obj = value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
  const props = schema.properties ?? {};
  const required = new Set(schema.required ?? []);
  const isRoot = path === "";

  const body = (
    <>
      {Object.entries(props).map(([k, subSchema]) => (
        <div key={k}>
          <Field
            schema={subSchema}
            value={obj[k]}
            path={path ? `${path}.${k}` : k}
            onChange={onChange}
            registerRef={registerRef}
          />
          {required.has(k) && (obj[k] === undefined || obj[k] === "" || obj[k] === null) && (
            <small style={{ color: "var(--error)", fontSize: 10 }}>required</small>
          )}
        </div>
      ))}
    </>
  );

  if (isRoot) return body; // 根 object 不包 fieldset

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
          {key}
        </span>
      </legend>
      {body}
    </fieldset>
  );
}
