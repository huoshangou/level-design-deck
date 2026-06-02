import { useCallback, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useEditorStore } from "../stores/editorStore";
import { useSpecList } from "../hooks/useSpec";
import SpecPicker from "./SpecPicker";
import type { ModuleInfo } from "../api/types";

type Props = {
  onPreviewRefresh: () => void;
  chatOpen: boolean;
  onToggleChat: () => void;
};

export default function Topbar({ onPreviewRefresh, chatOpen, onToggleChat }: Props) {
  const qc = useQueryClient();
  const { data: list } = useSpecList();
  const {
    currentSpecId,
    localContent,
    dirty,
    selectSpec,
    markClean,
    showToast,
  } = useEditorStore();
  const [busy, setBusy] = useState<string | null>(null);

  const currentInfo = list?.specs.find((s) => s.id === currentSpecId) ?? null;
  const levelId = currentInfo?.level_id ?? null;

  async function withBusy<T>(label: string, fn: () => Promise<T>): Promise<T | null> {
    setBusy(label);
    try {
      const r = await fn();
      return r;
    } catch (e) {
      showToast("err", `${label} 失败：${String(e)}`);
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function onSave() {
    if (!currentSpecId || !localContent) return;
    const r = await withBusy("保存", () => api.saveSpec(currentSpecId, localContent));
    if (r) {
      markClean();
      qc.invalidateQueries({ queryKey: ["spec", currentSpecId] });
      qc.invalidateQueries({ queryKey: ["specs"] });
      showToast("ok", `已保存 mtime=${r.mtime.toFixed(0)}`);
    }
  }

  async function onRecheck() {
    if (!currentSpecId) return;
    await withBusy("重跑校验", async () => {
      await qc.invalidateQueries({ queryKey: ["check", currentSpecId] });
      if (levelId) await qc.invalidateQueries({ queryKey: ["cross", levelId] });
    });
  }

  async function onRender() {
    if (!currentSpecId) return;
    const r = await withBusy("渲染 spec", () => api.renderSpec(currentSpecId));
    if (r) {
      showToast("ok", `渲染 ${r.size_bytes}B → ${r.output_path}`);
      onPreviewRefresh();
    }
  }

  async function onRenderLevel() {
    if (!levelId) return showToast("err", "当前 spec 无 level_id");
    const r = await withBusy("完整文档", () => api.renderLevel(levelId, true));
    if (r) {
      showToast("ok", `${r.modules.length} module → ${r.output_path}`);
      window.open(`/outputs/${r.output_path.split("/").pop()}`, "_blank");
    }
  }

  async function onDeck() {
    if (!levelId) return showToast("err", "当前 spec 无 level_id");
    const r = await withBusy("Deck", () => api.renderDeck(levelId));
    if (r) {
      showToast("ok", `Deck → ${r.output_path}`);
      window.open(`/outputs/${r.output_path.split("/").pop()}`, "_blank");
    }
  }

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 16px",
        borderBottom: "1px solid var(--border)",
        background: "var(--panel)",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <strong style={{ fontSize: 13, color: "var(--accent)" }}>level-design-deck</strong>
      <SpecPicker specs={list?.specs ?? []} currentId={currentSpecId} onSelect={selectSpec} />
      <CreateSpecBtn
        onCreated={(specId) => {
          qc.invalidateQueries({ queryKey: ["specs"] });
          selectSpec(specId);
        }}
      />
      {levelId && (
        <span style={{ fontSize: 11, color: "var(--text-faint)", fontFamily: "var(--mono)" }}>
          level={levelId}
        </span>
      )}
      <span style={{ flex: 1 }} />
      <DirtyBadge dirty={dirty} />
      <Btn onClick={onSave} disabled={!dirty || !!busy} kind="primary">
        💾 保存
      </Btn>
      <Btn onClick={onRecheck} disabled={!currentSpecId || !!busy}>↻ 重跑校验</Btn>
      <Btn onClick={onRender} disabled={!currentSpecId || !!busy}>🎨 渲染</Btn>
      <Btn onClick={onRenderLevel} disabled={!levelId || !!busy}>📚 完整文档</Btn>
      <Btn onClick={onDeck} disabled={!levelId || !!busy}>🎞 Deck</Btn>
      {busy && <span style={{ fontSize: 11, color: "var(--text-faint)" }}>… {busy}</span>}
      <DocTemplatesBtn />
      <Btn onClick={onToggleChat}>{chatOpen ? "💬▶" : "◀💬"}</Btn>
    </header>
  );
}

// ── 文档模板下拉 ─────────────────────────────────────────────────────────────

interface DocTemplateInfo {
  filename: string;
  kind: string;
  version: string;
  url: string;
  has_fields_json: boolean;
}

const KIND_LABEL: Record<string, string> = {
  gameplay: "玩法设计",
  prop: "物件需求",
};

function DocTemplatesBtn() {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const { openDocTemplate, docTemplateUrl } = useEditorStore();

  const { data: templates = [] } = useQuery<DocTemplateInfo[]>({
    queryKey: ["doc-templates"],
    queryFn: () => fetch("/api/doc-templates").then((r) => r.json()),
    staleTime: 60_000,
  });

  if (templates.length === 0) return null;

  function handleSelect(t: DocTemplateInfo) {
    openDocTemplate(t.url, `${KIND_LABEL[t.kind] ?? t.kind} 模板 v${t.version}`);
    setOpen(false);
  }

  return (
    <div style={{ position: "relative" }}>
      <button
        ref={btnRef}
        onClick={() => setOpen((v) => !v)}
        style={{
          padding: "4px 10px",
          fontSize: 12,
          border: `1px solid ${docTemplateUrl ? "var(--accent)" : "var(--border)"}`,
          borderRadius: 3,
          background: docTemplateUrl ? "var(--accent-bg)" : "var(--panel)",
          color: docTemplateUrl ? "var(--accent)" : "var(--text)",
          cursor: "pointer",
        }}
      >
        📄 {docTemplateUrl ? "文档模板 ●" : "文档模板"}
      </button>
      {open && (
        <>
          <div
            style={{ position: "fixed", inset: 0, zIndex: 19 }}
            onClick={() => setOpen(false)}
          />
          <div
            style={{
              position: "absolute",
              top: "calc(100% + 4px)",
              right: 0,
              zIndex: 20,
              background: "var(--panel)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              boxShadow: "var(--shadow)",
              minWidth: 220,
              padding: "4px 0",
            }}
          >
            <div style={{ padding: "4px 12px 6px", fontSize: 10, color: "var(--text-faint)", letterSpacing: 1 }}>
              在预览栏打开可编辑模板
            </div>
            {templates.map((t) => (
              <div
                key={t.filename}
                onClick={() => handleSelect(t)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  fontSize: 12,
                  color: "var(--text)",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-bg)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "")}
              >
                <span style={{
                  fontSize: 10,
                  padding: "1px 5px",
                  borderRadius: 2,
                  background: "var(--accent-bg)",
                  color: "var(--accent)",
                  fontWeight: 600,
                  flexShrink: 0,
                }}>
                  {KIND_LABEL[t.kind] ?? t.kind}
                </span>
                <span style={{ flex: 1 }}>{t.filename.replace(/_template_v[\d.]+\.html$/, "")}</span>
                <span style={{ fontSize: 10, color: "var(--text-faint)" }}>v{t.version}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function DirtyBadge({ dirty }: { dirty: boolean }) {
  return (
    <span
      style={{
        fontSize: 11,
        padding: "2px 6px",
        borderRadius: 2,
        background: dirty ? "var(--review)" : "transparent",
        color: dirty ? "#fff" : "var(--text-faint)",
      }}
    >
      {dirty ? "● 未保存" : "✓ 已保存"}
    </span>
  );
}

// ── 新建 spec ──────────────────────────────────────────────────────────────

function buildSkeleton(schema: Record<string, unknown>, specId: string, levelId: string): Record<string, unknown> {
  const props = (schema.properties ?? {}) as Record<string, Record<string, unknown>>;
  const result: Record<string, unknown> = {};

  for (const [key, fieldSchema] of Object.entries(props)) {
    const fieldType = fieldSchema.type as string;
    if (fieldType === "object") {
      const subProps = (fieldSchema.properties ?? {}) as Record<string, Record<string, unknown>>;
      const subRequired = new Set((fieldSchema.required ?? []) as string[]);
      const obj: Record<string, unknown> = {};
      for (const [sk, sv] of Object.entries(subProps)) {
        if (subRequired.has(sk) || sk === "spec_id" || sk === "level_id" || sk === "version" || sk === "owner") {
          const st = sv.type as string;
          if (sk === "spec_id") obj[sk] = specId;
          else if (sk === "level_id") obj[sk] = levelId;
          else if (sk === "version") obj[sk] = "0.1.0";
          else if (sk === "owner") obj[sk] = (sv.default as string) ?? "level";
          else if (st === "string") obj[sk] = sv.enum ? (sv.enum as string[])[0] : "";
          else if (st === "number" || st === "integer") obj[sk] = 0;
          else if (st === "boolean") obj[sk] = false;
          else if (st === "array") obj[sk] = [];
          else obj[sk] = "";
        }
      }
      result[key] = obj;
    } else if (fieldType === "array") {
      result[key] = [];
    } else if (fieldType === "string") {
      result[key] = (fieldSchema.default as string) ?? "";
    }
  }
  return result;
}

function CreateSpecBtn({ onCreated }: { onCreated: (specId: string) => void }) {
  const [open, setOpen] = useState(false);
  const [selectedModule, setSelectedModule] = useState("");
  const [levelId, setLevelId] = useState("");
  const [creating, setCreating] = useState(false);

  const { data: modules } = useQuery<{ modules: ModuleInfo[] }>({
    queryKey: ["modules"],
    queryFn: () => api.listModules(),
    staleTime: 60_000,
  });

  const handleCreate = useCallback(async () => {
    if (!selectedModule || !levelId.trim()) return;
    setCreating(true);
    try {
      const schema = await api.getModuleSchema(selectedModule);
      const specId = `${selectedModule}_${levelId.trim().replace(/[^a-z0-9_]/gi, "_").toLowerCase()}`;
      const skeleton = buildSkeleton(schema, specId, levelId.trim());
      await api.saveSpec(specId, skeleton);
      onCreated(specId);
      setOpen(false);
      setSelectedModule("");
      setLevelId("");
    } catch (e) {
      alert(`创建失败：${String(e)}`);
    } finally {
      setCreating(false);
    }
  }, [selectedModule, levelId, onCreated]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        style={{
          padding: "4px 8px",
          fontSize: 12,
          border: "1px solid var(--border)",
          borderRadius: 3,
          background: "var(--panel)",
          color: "var(--accent)",
          cursor: "pointer",
          fontWeight: 600,
        }}
      >
        + 新建
      </button>
      {open && (
        <>
          <div
            style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)", zIndex: 50 }}
            onClick={() => setOpen(false)}
          />
          <div style={{
            position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
            zIndex: 51, background: "var(--panel)", border: "1px solid var(--border)",
            borderRadius: 8, boxShadow: "var(--shadow)", padding: 24, minWidth: 360,
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>新建 spec</div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 4 }}>Module 类型</div>
              <select
                value={selectedModule}
                onChange={(e) => setSelectedModule(e.target.value)}
                style={{
                  width: "100%", padding: "6px 8px", fontSize: 12,
                  border: "1px solid var(--border)", borderRadius: 3,
                  background: "var(--surface)",
                }}
              >
                <option value="">— 选择 module —</option>
                {(modules?.modules ?? []).map((m) => (
                  <option key={m.name} value={m.name}>{m.name}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 4 }}>Level ID</div>
              <input
                value={levelId}
                onChange={(e) => setLevelId(e.target.value)}
                placeholder="如 abandoned_temple"
                style={{
                  width: "100%", padding: "6px 8px", fontSize: 12,
                  border: "1px solid var(--border)", borderRadius: 3,
                  background: "var(--surface)", boxSizing: "border-box",
                }}
              />
            </div>

            {selectedModule && levelId.trim() && (
              <div style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 12, fontFamily: "var(--mono)" }}>
                spec_id: {selectedModule}_{levelId.trim().replace(/[^a-z0-9_]/gi, "_").toLowerCase()}
              </div>
            )}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setOpen(false)}
                style={{ padding: "6px 14px", fontSize: 12, border: "1px solid var(--border)", borderRadius: 3, background: "var(--panel)", cursor: "pointer" }}
              >
                取消
              </button>
              <button
                onClick={() => void handleCreate()}
                disabled={!selectedModule || !levelId.trim() || creating}
                style={{
                  padding: "6px 14px", fontSize: 12, border: "none", borderRadius: 3,
                  background: selectedModule && levelId.trim() ? "var(--accent)" : "var(--border)",
                  color: selectedModule && levelId.trim() ? "#fff" : "var(--text-faint)",
                  cursor: selectedModule && levelId.trim() && !creating ? "pointer" : "default",
                }}
              >
                {creating ? "创建中…" : "创建"}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function Btn({
  children,
  onClick,
  disabled,
  kind,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  kind?: "primary";
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "4px 10px",
        fontSize: 12,
        border: "1px solid var(--border)",
        borderRadius: 3,
        background: kind === "primary" ? "var(--accent)" : "var(--panel)",
        color: kind === "primary" ? "#fff" : "var(--text)",
        opacity: disabled ? 0.4 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {children}
    </button>
  );
}
