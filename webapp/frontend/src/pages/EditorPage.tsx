import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import Topbar from "../components/Topbar";
import AlertsSidebar from "../components/AlertsSidebar";
import PreviewPane from "../components/PreviewPane";
import SchemaForm, { type SchemaFormHandle } from "../components/form/SchemaForm";
import BubbleDiagramView from "../components/BubbleDiagramView";
import SpatialLayoutView from "../components/SpatialLayoutView";
import ChatSidebar from "../components/chat/ChatSidebar";
import WorkspacePanel from "../components/WorkspacePanel";
import { useEditorStore } from "../stores/editorStore";
import { useSpec, useSpecList, useModuleSchema } from "../hooks/useSpec";
import { useChecks } from "../hooks/useChecks";
import { useQueryClient } from "@tanstack/react-query";

// 水平可拖分割条
function HDivider({ onDrag }: { onDrag: (dx: number) => void }) {
  const startX = useRef<number | null>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    startX.current = e.clientX;
    function onMove(ev: MouseEvent) {
      if (startX.current === null) return;
      onDrag(ev.clientX - startX.current);
      startX.current = ev.clientX;
    }
    function onUp() {
      startX.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [onDrag]);

  return (
    <div
      onMouseDown={onMouseDown}
      style={{
        width: 5,
        flexShrink: 0,
        cursor: "ew-resize",
        background: "var(--border)",
        transition: "background 0.1s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "var(--border)")}
    />
  );
}

export default function EditorPage() {
  const { currentSpecId, localContent, updateField, toast, clearToast, selectSpec, docTemplateUrl, docTemplateLabel } = useEditorStore();
  const { data: list } = useSpecList();
  useSpec(currentSpecId);
  const queryClient = useQueryClient();

  const currentInfo = list?.specs.find((s) => s.id === currentSpecId) ?? null;
  const module = currentInfo?.module ?? null;
  const levelId = currentInfo?.level_id ?? null;
  const { data: schema } = useModuleSchema(module);

  const { alerts, isLoading: checksLoading } = useChecks(currentSpecId, levelId);
  const [previewKey, setPreviewKey] = useState(0);
  const [chatOpen, setChatOpen] = useState(true);
  const formRef = useRef<SchemaFormHandle>(null);

  // 可拖宽度（px）
  const [alertsW, setAlertsW] = useState(280);
  const [previewW, setPreviewW] = useState(320);
  const [chatW, setChatW] = useState(300);
  const [workspaceW, setWorkspaceW] = useState(280);

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
        {/* 模板模式：用 Workspace 面板替代告警栏 + spec 编辑区，预览栏占满 */}
        {docTemplateUrl ? (
          <>
            <WorkspacePanel width={workspaceW} />
            <HDivider onDrag={(dx) => setWorkspaceW((w) => Math.max(200, Math.min(520, w + dx)))} />
            <section style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 200 }}>
              <h2 style={SECTION_TITLE}>📄 {docTemplateLabel ?? "文档模板"}</h2>
              <div style={{ flex: 1, overflow: "hidden" }}>
                <PreviewPane specId={currentSpecId} refreshKey={previewKey} />
              </div>
            </section>
            {chatOpen && (
              <>
                <HDivider onDrag={(dx) => setChatW((w) => Math.max(200, Math.min(560, w - dx)))} />
                <div style={{ width: chatW, flexShrink: 0 }}>
                  <ChatSidebar />
                </div>
              </>
            )}
          </>
        ) : (
          <>
            {/* 告警栏 */}
            <AlertsSidebar
              alerts={alerts}
              isLoading={checksLoading}
              onJump={(p) => formRef.current?.jumpTo(p)}
              width={alertsW}
            />
            <HDivider onDrag={(dx) => setAlertsW((w) => Math.max(160, Math.min(520, w + dx)))} />

            {/* 主编辑区 */}
            <main style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column", minWidth: 200 }}>
              {!currentSpecId ? (
                <Empty />
              ) : module === "bubble_diagram" ? (
                <BubbleDiagramSplit
                  nodes={(localContent?.nodes as Parameters<typeof BubbleDiagramView>[0]["nodes"]) ?? []}
                  edges={(localContent?.edges as Parameters<typeof BubbleDiagramView>[0]["edges"]) ?? []}
                  schema={schema ?? null}
                  value={localContent}
                  onChange={updateField}
                  formRef={formRef}
                />
              ) : module === "spatial_layout" ? (
                <SpatialLayoutView
                  specId={currentSpecId}
                  layout={localContent?.layout ?? null}
                  onSaved={() => {
                    void queryClient.invalidateQueries({ queryKey: ["spec", currentSpecId] });
                    setPreviewKey((k) => k + 1);
                  }}
                />
              ) : (
                <div style={{ flex: 1, overflow: "auto" }}>
                  <SchemaForm
                    ref={formRef}
                    schema={schema ?? null}
                    value={localContent}
                    onChange={updateField}
                  />
                </div>
              )}
            </main>

            <HDivider onDrag={(dx) => setPreviewW((w) => Math.max(160, Math.min(600, w - dx)))} />

            {/* 预览栏 */}
            <section
              style={{
                width: previewW,
                flexShrink: 0,
                display: "flex",
                flexDirection: "column",
              }}
            >
              <h2 style={SECTION_TITLE}>
                预览 · /outputs/{currentSpecId ?? "—"}.html
              </h2>
              <div style={{ flex: 1, overflow: "hidden" }}>
                <PreviewPane specId={currentSpecId} refreshKey={previewKey} />
              </div>
            </section>

            {chatOpen && (
              <>
                <HDivider onDrag={(dx) => setChatW((w) => Math.max(200, Math.min(560, w - dx)))} />
                <div style={{ width: chatW, flexShrink: 0 }}>
                  <ChatSidebar />
                </div>
              </>
            )}
          </>
        )}
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
            background: toast.kind === "ok" ? "var(--success)" : "var(--error)",
            borderRadius: 4,
            boxShadow: "var(--shadow)",
            zIndex: 100,
          }}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}

// ── BubbleDiagramSplit: 上 Mermaid 图 + 下 SchemaForm，点节点跳到对应编辑区 ──────

interface BubbleSplitProps {
  nodes: Parameters<typeof BubbleDiagramView>[0]["nodes"];
  edges: Parameters<typeof BubbleDiagramView>[0]["edges"];
  schema: Record<string, unknown> | null;
  value: Record<string, unknown> | null;
  onChange: (path: string, value: unknown) => void;
  formRef: RefObject<SchemaFormHandle | null>;
}

function BubbleDiagramSplit({ nodes, edges, schema, value, onChange, formRef }: BubbleSplitProps) {
  // path 格式：nodes[0]、nodes[1]（与 ArrayField 里 `${path}[${i}]` 一致）
  function handleNodeClick(nodeId: string) {
    const idx = nodes.findIndex((n) => n.id === nodeId);
    if (idx >= 0) formRef.current?.jumpTo(`nodes[${idx}]`);
  }

  // 可拖动分割线
  const [topPct, setTopPct] = useState(40); // 上半占比 %
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
  }, []);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientY - rect.top) / rect.height) * 100;
      setTopPct(Math.min(80, Math.max(15, pct)));
    }
    function onUp() { dragging.current = false; }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  return (
    <div ref={containerRef} style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* 上半：Mermaid 图 */}
      <div style={{ height: `${topPct}%`, overflow: "auto", background: "var(--panel)", flexShrink: 0 }}>
        <BubbleDiagramView nodes={nodes} edges={edges} onNodeClick={handleNodeClick} />
      </div>

      {/* 拖动分割条 */}
      <div
        onMouseDown={onMouseDown}
        style={{
          height: 6,
          flexShrink: 0,
          cursor: "ns-resize",
          background: "var(--border)",
          borderTop: "1px solid var(--border)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          userSelect: "none",
        }}
      >
        <div style={{ width: 32, height: 2, background: "var(--text-faint)", borderRadius: 1 }} />
      </div>

      {/* 下半：SchemaForm */}
      <div style={{ flex: 1, overflow: "auto" }}>
        <SchemaForm ref={formRef} schema={schema} value={value} onChange={onChange} />
      </div>
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
