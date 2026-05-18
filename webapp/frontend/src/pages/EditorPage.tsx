import { useEffect, useRef, useState } from "react";
import Topbar from "../components/Topbar";
import AlertsSidebar from "../components/AlertsSidebar";
import PreviewPane from "../components/PreviewPane";
import SchemaForm, { type SchemaFormHandle } from "../components/form/SchemaForm";
import ChatSidebar from "../components/chat/ChatSidebar";
import { useEditorStore } from "../stores/editorStore";
import { useSpec, useSpecList, useModuleSchema } from "../hooks/useSpec";
import { useChecks } from "../hooks/useChecks";

export default function EditorPage() {
  const { currentSpecId, localContent, updateField, toast, clearToast, selectSpec } = useEditorStore();
  const { data: list } = useSpecList();
  useSpec(currentSpecId);

  const currentInfo = list?.specs.find((s) => s.id === currentSpecId) ?? null;
  const module = currentInfo?.module ?? null;
  const levelId = currentInfo?.level_id ?? null;
  const { data: schema } = useModuleSchema(module);

  const { alerts, isLoading: checksLoading } = useChecks(currentSpecId, levelId);
  const [previewKey, setPreviewKey] = useState(0);
  const [chatOpen, setChatOpen] = useState(true);
  const formRef = useRef<SchemaFormHandle>(null);

  // URL hash 同步
  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const fromHash = hash.get("spec");
    if (fromHash && fromHash !== currentSpecId) selectSpec(fromHash);
  }, []);
  useEffect(() => {
    const hash = new URLSearchParams();
    if (currentSpecId) hash.set("spec", currentSpecId);
    window.location.hash = hash.toString();
  }, [currentSpecId]);

  // toast 自动 3 秒消失
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(clearToast, 3000);
    return () => clearTimeout(t);
  }, [toast, clearToast]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Topbar
        onPreviewRefresh={() => setPreviewKey((k) => k + 1)}
        chatOpen={chatOpen}
        onToggleChat={() => setChatOpen((v) => !v)}
      />
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <AlertsSidebar
          alerts={alerts}
          isLoading={checksLoading}
          onJump={(p) => formRef.current?.jumpTo(p)}
        />
        <main style={{ flex: 1, overflow: "auto", borderRight: "1px solid var(--border)" }}>
          {currentSpecId ? (
            <SchemaForm
              ref={formRef}
              schema={schema ?? null}
              value={localContent}
              onChange={updateField}
            />
          ) : (
            <Empty />
          )}
        </main>
        <section
          style={{
            width: chatOpen ? "30%" : "40%",
            minWidth: chatOpen ? 280 : 360,
            display: "flex",
            flexDirection: "column",
            borderRight: chatOpen ? "1px solid var(--border)" : "none",
          }}
        >
          <h2 style={SECTION_TITLE}>预览 · /outputs/{currentSpecId ?? "—"}.html</h2>
          <div style={{ flex: 1, overflow: "hidden" }}>
            <PreviewPane specId={currentSpecId} refreshKey={previewKey} />
          </div>
        </section>
        {chatOpen && <ChatSidebar />}
      </div>
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: 16,
            right: 16,
            padding: "10px 16px",
            fontSize: 12,
            color: "#fff",
            background: toast.kind === "ok" ? "#1a73e8" : "var(--error)",
            borderRadius: 4,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            zIndex: 100,
          }}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}

function Empty() {
  return (
    <div style={{ padding: 40, textAlign: "center", color: "var(--text-faint)" }}>
      <h2 style={{ fontSize: 14 }}>选一个 spec 开始</h2>
      <p style={{ fontSize: 12 }}>顶部 dropdown 选 spec，或 URL 加 <code>#spec=lighting_req_xxx</code></p>
    </div>
  );
}

const SECTION_TITLE = {
  margin: 0,
  padding: "8px 12px",
  fontSize: 11,
  fontWeight: 600,
  color: "var(--text-dim)",
  borderBottom: "1px solid var(--border)",
  background: "var(--panel)",
  fontFamily: "var(--mono)",
} as const;
