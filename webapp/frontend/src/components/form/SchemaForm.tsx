// 顶层 form：包 Field 递归 + 暴露 fieldRefs 给 AlertsSidebar 跳转用。

import { forwardRef, useCallback, useImperativeHandle, useRef } from "react";
import Field from "./Field";

type Props = {
  schema: Record<string, unknown> | null;
  value: Record<string, unknown> | null;
  onChange: (path: string, value: unknown) => void;
};

export type SchemaFormHandle = {
  jumpTo: (path: string) => void;
};

const SchemaForm = forwardRef<SchemaFormHandle, Props>(function SchemaForm(
  { schema, value, onChange },
  ref,
) {
  const refs = useRef(new Map<string, HTMLElement>());

  const registerRef = useCallback((path: string, el: HTMLElement | null) => {
    if (el) refs.current.set(path, el);
    else refs.current.delete(path);
  }, []);

  useImperativeHandle(ref, () => ({
    jumpTo: (path: string) => {
      // 尝试精确命中；命中不到就退到前缀（祖先 fieldset）
      let el = refs.current.get(path);
      if (!el) {
        const segs = path.split(".");
        while (segs.length && !el) {
          segs.pop();
          el = refs.current.get(segs.join("."));
        }
      }
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.animate(
        [
          { background: "var(--accent-bg)" },
          { background: "var(--accent-bg)" },
          { background: "transparent" },
        ],
        { duration: 1500, easing: "ease-out" },
      );
      const focusable = el.querySelector<HTMLElement>("input, textarea, select");
      focusable?.focus();
    },
  }));

  if (!schema || !value) {
    return <div style={{ padding: 24, color: "var(--text-faint)", fontSize: 12 }}>无 spec / schema</div>;
  }

  return (
    <div style={{ padding: 24, maxWidth: 920, margin: "0 auto" }}>
      <Field schema={schema} value={value} path="" onChange={onChange} registerRef={registerRef} />
    </div>
  );
});

export default SchemaForm;
