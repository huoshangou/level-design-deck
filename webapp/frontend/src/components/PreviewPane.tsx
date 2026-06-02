import { useEffect, useState } from "react";
import { useEditorStore } from "../stores/editorStore";
import { api } from "../api/client";

type Props = {
  specId: string | null;
  refreshKey: number;
  onRender?: () => void;
};

export default function PreviewPane({ specId, refreshKey, onRender }: Props) {
  const { docTemplateUrl, docTemplateLabel, closeDocTemplate } = useEditorStore();
  const [exists, setExists] = useState<boolean | null>(null);
  const [rendering, setRendering] = useState(false);

  async function handleRenderClick() {
    if (!specId || rendering) return;
    if (onRender) { onRender(); return; }
    setRendering(true);
    try {
      await api.renderSpec(specId);
      setExists(true);
    } catch (e) {
      alert(`渲染失败：${String(e)}`);
    } finally {
      setRendering(false);
    }
  }

  useEffect(() => {
    if (!specId || docTemplateUrl) return;
    setExists(null);
    const url = `/outputs/${specId}.html`;
    fetch(url, { method: "HEAD" })
      .then((r) => setExists(r.ok))
      .catch(() => setExists(false));
  }, [specId, refreshKey, docTemplateUrl]);

  if (docTemplateUrl) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "4px 10px", background: "var(--panel)",
          borderBottom: "1px solid var(--border)", flexShrink: 0,
        }}>
          <span style={{ fontSize: 11, color: "var(--text-dim)", flex: 1, fontFamily: "var(--mono)" }}>
            {docTemplateLabel ?? docTemplateUrl}
          </span>
          <button
            onClick={closeDocTemplate}
            title="关闭模板，回到 spec 预览"
            style={{
              padding: "2px 8px", fontSize: 11, border: "1px solid var(--border)",
              borderRadius: 3, background: "var(--panel)", cursor: "pointer", color: "var(--text-dim)",
            }}
          >
            ✕ 关闭
          </button>
        </div>
        <iframe
          key={docTemplateUrl}
          title="doc-template"
          src={docTemplateUrl}
          style={{ flex: 1, border: "none", background: "#fff" }}
        />
      </div>
    );
  }

  if (!specId) {
    return (
      <div style={{ padding: 16, color: "var(--text-faint)", fontSize: 12 }}>无 spec 选中</div>
    );
  }

  if (exists === null) {
    return (
      <div style={{ padding: 16, color: "var(--text-faint)", fontSize: 12 }}>检查预览…</div>
    );
  }

  if (!exists) {
    return (
      <div style={{
        height: "100%", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: 12,
        color: "var(--text-faint)",
      }}>
        <div style={{ fontSize: 24, opacity: 0.3 }}>🎨</div>
        <div style={{ fontSize: 12, textAlign: "center", lineHeight: 1.6 }}>
          尚未生成预览<br />
          <span style={{ fontSize: 11, color: "var(--text-faint)" }}>点击顶部「渲染」按钮生成</span>
        </div>
        <button
          onClick={() => void handleRenderClick()}
          disabled={rendering}
          style={{
            padding: "6px 16px", fontSize: 12, border: "none",
            borderRadius: 3, background: "var(--accent)", color: "#fff",
            cursor: rendering ? "wait" : "pointer",
            opacity: rendering ? 0.6 : 1,
          }}
        >
          {rendering ? "渲染中…" : "🎨 渲染"}
        </button>
      </div>
    );
  }

  return (
    <iframe
      key={`${specId}-${refreshKey}`}
      title={`preview-${specId}`}
      src={`/outputs/${specId}.html?v=${refreshKey}`}
      style={{ width: "100%", height: "100%", border: "none", background: "#fff" }}
    />
  );
}
