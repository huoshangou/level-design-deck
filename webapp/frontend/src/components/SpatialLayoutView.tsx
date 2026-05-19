import { useRef, useState } from "react";
import { api } from "../api/client";

interface Props {
  specId: string;
  layout: unknown; // spec.layout field (JSON or null)
  onSaved: () => void;
}

export default function SpatialLayoutView({ specId, layout, onSaved }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  function showMsg(text: string, ok = true) {
    setMsg(text);
    setTimeout(() => setMsg(null), 3000);
    void ok;
  }

  async function handleImportJson(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      setSaving(true);
      // load full spec, merge layout field, save
      const record = await api.getSpec(specId);
      const updated = { ...record.content, layout: json };
      await api.saveSpec(specId, updated);
      showMsg("layout 已导入并保存");
      onSaved();
    } catch (err) {
      showMsg(`导入失败: ${err}`, false);
    } finally {
      setSaving(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function openEditor() {
    // open LevelCraft in new tab; user edits and exports JSON, then imports back
    window.open("/tools/levelcraft/editor.html", "_blank");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* toolbar */}
      <div
        style={{
          display: "flex",
          gap: 8,
          padding: "8px 12px",
          borderBottom: "1px solid var(--border)",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        <button onClick={openEditor} style={BTN}>
          🗺 打开 LevelCraft 编辑器
        </button>
        <label style={{ ...BTN, cursor: "pointer" }}>
          📂 Import JSON
          <input
            ref={fileRef}
            type="file"
            accept=".json"
            style={{ display: "none" }}
            onChange={handleImportJson}
            disabled={saving}
          />
        </label>
        {msg && (
          <span style={{ fontSize: 11, color: "var(--text-dim)", marginLeft: 4 }}>{msg}</span>
        )}
        {saving && <span style={{ fontSize: 11, color: "var(--text-dim)" }}>保存中…</span>}
      </div>

      {/* layout preview or empty state */}
      <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {layout ? (
          <LayoutPreview layout={layout} />
        ) : (
          <div style={{ color: "var(--text-faint)", fontSize: 13, textAlign: "center", paddingTop: 48 }}>
            <p>暂无 layout 数据</p>
            <p style={{ fontSize: 11, marginTop: 4 }}>
              点「打开 LevelCraft 编辑器」，在编辑器内设计后导出 JSON，再「Import JSON」替换此字段
            </p>
          </div>
        )}
      </div>
      <iframe ref={iframeRef} style={{ display: "none" }} title="levelcraft-hidden" />
    </div>
  );
}

function LayoutPreview({ layout }: { layout: unknown }) {
  // minimal JSON tree preview — full render happens via /api/render in PreviewPane
  const json = JSON.stringify(layout, null, 2);
  const lines = json.split("\n").length;
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 8 }}>
        layout 数据已加载（{lines} 行）— 点「🎨 渲染」在预览栏查看 2D/3D 图
      </p>
      <pre
        style={{
          fontSize: 10,
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "8px 10px",
          overflow: "auto",
          maxHeight: 400,
          lineHeight: 1.4,
        }}
      >
        {json.length > 4000 ? json.slice(0, 4000) + "\n… (截断)" : json}
      </pre>
    </div>
  );
}

const BTN: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: 11,
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--panel)",
  color: "var(--text)",
  cursor: "pointer",
};
