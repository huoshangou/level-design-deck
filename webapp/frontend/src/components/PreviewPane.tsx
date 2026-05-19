import { useEditorStore } from "../stores/editorStore";

type Props = {
  specId: string | null;
  refreshKey: number;
};

export default function PreviewPane({ specId, refreshKey }: Props) {
  const { docTemplateUrl, docTemplateLabel, closeDocTemplate } = useEditorStore();

  // 文档模板模式：预览栏显示可编辑 HTML 模板
  if (docTemplateUrl) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "4px 10px",
          background: "var(--panel)",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 11, color: "var(--text-dim)", flex: 1, fontFamily: "var(--mono)" }}>
            {docTemplateLabel ?? docTemplateUrl}
          </span>
          <button
            onClick={closeDocTemplate}
            title="关闭模板，回到 spec 预览"
            style={{
              padding: "2px 8px",
              fontSize: 11,
              border: "1px solid var(--border)",
              borderRadius: 3,
              background: "var(--panel)",
              cursor: "pointer",
              color: "var(--text-dim)",
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

  // 普通模式：显示 spec 渲染输出
  if (!specId) {
    return (
      <div style={{ padding: 16, color: "var(--text-faint)", fontSize: 12 }}>
        无 spec 选中
      </div>
    );
  }
  return (
    <iframe
      title={`preview-${specId}`}
      src={`/outputs/${specId}.html?v=${refreshKey}`}
      style={{ width: "100%", height: "100%", border: "none", background: "#fff" }}
    />
  );
}
