// Workspace 资源面板（模板模式下代替告警栏）：递归任务树 + 文档/素材列表 + 新建任务弹层。

import { useEffect, useState } from "react";
import { useWorkspaceStore } from "../stores/workspaceStore";
import { useEditorStore } from "../stores/editorStore";
import { useChatStore } from "../stores/chatStore";
import type { TaskKind, WorkspaceTask } from "../api/client";
import { api } from "../api/client";

const KIND_LABEL: Record<TaskKind, string> = {
  poi: "POI",
  gameplay: "玩法",
  prop: "物件",
};

const KIND_COLOR: Record<TaskKind, string> = {
  poi: "var(--accent)",
  gameplay: "#1F7A4D",
  prop: "#C4862E",
};

export default function WorkspacePanel({ width }: { width: number }) {
  const { tree, loading, error, refresh } = useWorkspaceStore();
  const [createCtx, setCreateCtx] = useState<{ parent_path: string; kind: TaskKind } | null>(null);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <aside
      style={{
        width,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid var(--border)",
        background: "var(--panel)",
        overflow: "hidden",
      }}
    >
      <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border)", background: "var(--surface)", display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-dim)", letterSpacing: 1, flex: 1, fontFamily: "var(--mono)" }}>
          📁 WORKSPACE
        </span>
        <ImportMenu onDone={refresh} />
        <button
          onClick={() => setCreateCtx({ parent_path: "", kind: "poi" })}
          title="新建顶级 POI"
          style={{
            padding: "3px 8px", fontSize: 11,
            border: "1px solid var(--border)", borderRadius: 3,
            background: "var(--panel)", color: "var(--text)", cursor: "pointer",
          }}
        >
          + POI
        </button>
        <button
          onClick={() => void refresh()}
          title="刷新"
          style={{
            padding: "3px 6px", fontSize: 11,
            border: "1px solid var(--border)", borderRadius: 3,
            background: "var(--panel)", color: "var(--text-dim)", cursor: "pointer",
          }}
        >
          ↻
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "6px 0", fontSize: 12 }}>
        {loading && <div style={{ padding: 12, color: "var(--text-faint)" }}>加载中…</div>}
        {error && <div style={{ padding: 12, color: "var(--error)" }}>{error}</div>}
        {!loading && !error && tree && tree.tasks.length === 0 && (
          <div style={{ padding: 16, color: "var(--text-faint)", textAlign: "center", lineHeight: 1.6 }}>
            空 workspace<br />
            <span style={{ fontSize: 11 }}>点上方「+ POI」开始</span>
          </div>
        )}
        {!loading && tree && tree.tasks.map((t) => (
          <TaskNode key={t.path} task={t} depth={0} onCreateChild={setCreateCtx} />
        ))}
        {tree && (
          <div style={{ padding: "12px 12px 8px", fontSize: 10, color: "var(--text-faint)", borderTop: "1px solid var(--border-faint)", marginTop: 8 }}>
            <div style={{ fontFamily: "var(--mono)" }}>{tree.root}</div>
          </div>
        )}
      </div>

      {createCtx && (
        <CreateTaskModal
          parentPath={createCtx.parent_path}
          defaultKind={createCtx.kind}
          onClose={() => setCreateCtx(null)}
        />
      )}
    </aside>
  );
}

// ── 递归节点 ────────────────────────────────────────────────────────────

function TaskNode({ task, depth, onCreateChild }: {
  task: WorkspaceTask;
  depth: number;
  onCreateChild: (ctx: { parent_path: string; kind: TaskKind }) => void;
}) {
  const isExpanded = useWorkspaceStore((s) => s.isExpanded(task.path));
  const toggleExpand = useWorkspaceStore((s) => s.toggleExpand);
  const deleteTask = useWorkspaceStore((s) => s.deleteTask);
  const [detailOpen, setDetailOpen] = useState(false);
  const hasChildren = task.children.length > 0;

  const indent = 10 + depth * 14;

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "4px 8px",
          paddingLeft: indent,
          cursor: "default",
          userSelect: "none",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        <span
          onClick={() => toggleExpand(task.path)}
          style={{ width: 12, cursor: "pointer", color: "var(--text-faint)", textAlign: "center", fontSize: 10 }}
        >
          {hasChildren || task.doc_count + task.material_count > 0 ? (isExpanded ? "▼" : "▶") : "·"}
        </span>
        <span
          onClick={() => setDetailOpen((v) => !v)}
          style={{ flex: 1, cursor: "pointer", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
          title={task.desc || task.name}
        >
          <span style={{
            display: "inline-block",
            fontSize: 9,
            padding: "0 4px",
            marginRight: 4,
            background: KIND_COLOR[task.kind] + "20",
            color: KIND_COLOR[task.kind],
            borderRadius: 2,
            fontWeight: 600,
            verticalAlign: "1px",
          }}>
            {KIND_LABEL[task.kind]}
          </span>
          {task.name}
          {(task.doc_count > 0 || task.material_count > 0) && (
            <span style={{ marginLeft: 6, color: "var(--text-faint)", fontSize: 10 }}>
              {task.doc_count > 0 && `📄${task.doc_count}`}
              {task.material_count > 0 && ` 📦${task.material_count}`}
            </span>
          )}
        </span>
        <TaskActions task={task} onCreateChild={onCreateChild} onDelete={() => {
          if (confirm(`删除任务「${task.name}」？\n（含 ${task.doc_count} 个文档、${task.material_count} 个素材、${task.children.length} 个子任务，不可恢复）`)) {
            void deleteTask(task.path);
          }
        }} />
      </div>

      {isExpanded && (
        <>
          {/* 文档列表 */}
          {task.doc_count > 0 && <DocList taskPath={task.path} depth={depth + 1} />}
          {/* 素材列表 */}
          {task.material_count > 0 && <MaterialList taskPath={task.path} depth={depth + 1} />}
          {/* 关联对话 */}
          {task.session_count > 0 && <SessionList taskPath={task.path} depth={depth + 1} />}
          {/* 子任务 */}
          {task.children.map((c) => (
            <TaskNode key={c.path} task={c} depth={depth + 1} onCreateChild={onCreateChild} />
          ))}
        </>
      )}

      {detailOpen && task.desc && (
        <div style={{
          margin: `2px ${indent}px 4px ${indent + 16}px`,
          padding: "4px 8px",
          fontSize: 11,
          color: "var(--text-dim)",
          background: "var(--surface)",
          borderRadius: 3,
          borderLeft: `2px solid ${KIND_COLOR[task.kind]}`,
        }}>
          {task.desc}
        </div>
      )}
    </div>
  );
}

// ── 任务操作（右侧按钮）────────────────────────────────────────────────

function TaskActions({ task, onCreateChild, onDelete }: {
  task: WorkspaceTask;
  onCreateChild: (ctx: { parent_path: string; kind: TaskKind }) => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ position: "relative", flexShrink: 0 }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        style={{ border: "none", background: "transparent", cursor: "pointer", padding: "0 4px", color: "var(--text-faint)", fontSize: 14 }}
        title="操作"
      >
        ⋯
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 60 }} />
          <div
            style={{
              position: "absolute", right: 0, top: "100%",
              zIndex: 61, minWidth: 140,
              background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 4,
              boxShadow: "var(--shadow)", padding: "4px 0", fontSize: 12,
            }}
          >
            {task.kind === "poi" && (
              <>
                <ActionItem onClick={() => { setOpen(false); onCreateChild({ parent_path: task.path, kind: "gameplay" }); }}>+ 子玩法</ActionItem>
                <ActionItem onClick={() => { setOpen(false); onCreateChild({ parent_path: task.path, kind: "prop" }); }}>+ 子物件</ActionItem>
              </>
            )}
            {task.kind === "gameplay" && (
              <ActionItem onClick={() => { setOpen(false); onCreateChild({ parent_path: task.path, kind: "prop" }); }}>+ 子物件</ActionItem>
            )}
            <ActionItem danger onClick={() => { setOpen(false); onDelete(); }}>删除任务</ActionItem>
          </div>
        </>
      )}
    </span>
  );
}

function ActionItem({ children, onClick, danger }: { children: React.ReactNode; onClick: () => void; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "block", width: "100%", textAlign: "left",
        padding: "5px 12px", border: "none", background: "transparent",
        color: danger ? "var(--error)" : "var(--text)", cursor: "pointer", fontSize: 12,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      {children}
    </button>
  );
}

// ── 文档列表（任务下的 docs/ ）────────────────────────────────────────

function DocList({ taskPath, depth }: { taskPath: string; depth: number }) {
  const [items, setItems] = useState<{ filename: string; mtime: number }[] | null>(null);
  const openDocTemplate = useEditorStore((s) => s.openDocTemplate);

  useEffect(() => {
    api.getTask(taskPath).then((d) => setItems(d.docs)).catch(() => setItems([]));
  }, [taskPath]);

  if (!items || items.length === 0) return null;
  const indent = 10 + depth * 14;

  return (
    <div>
      {items.map((d) => (
        <div
          key={d.filename}
          onClick={() => openDocTemplate(
            `/workspace-file/${taskPath.split("/").map(encodeURIComponent).join("/")}/docs/${encodeURIComponent(d.filename)}`,
            `📄 ${d.filename}`,
          )}
          style={{
            padding: "3px 8px", paddingLeft: indent + 14,
            cursor: "pointer", color: "var(--text)",
            fontSize: 11, display: "flex", alignItems: "center", gap: 4,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          title={d.filename}
        >
          <span>📄</span>
          <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.filename}</span>
        </div>
      ))}
    </div>
  );
}

// ── 素材列表 ────────────────────────────────────────────────────────────

function MaterialList({ taskPath, depth }: { taskPath: string; depth: number }) {
  const [items, setItems] = useState<{ filename: string }[] | null>(null);
  useEffect(() => {
    api.getTask(taskPath).then((d) => setItems(d.materials)).catch(() => setItems([]));
  }, [taskPath]);
  if (!items || items.length === 0) return null;
  const indent = 10 + depth * 14;
  return (
    <div>
      {items.map((m) => (
        <div
          key={m.filename}
          style={{
            padding: "3px 8px", paddingLeft: indent + 14,
            color: "var(--text-dim)", fontSize: 11,
            display: "flex", alignItems: "center", gap: 4,
          }}
          title={m.filename}
        >
          <span>📦</span>
          <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.filename}</span>
        </div>
      ))}
    </div>
  );
}

// ── 关联对话 ────────────────────────────────────────────────────────────

function SessionList({ taskPath, depth }: { taskPath: string; depth: number }) {
  const [items, setItems] = useState<{ cc_session_id: string; note: string }[] | null>(null);
  const loadHistorySession = useChatStore((s) => s.loadHistorySession);
  useEffect(() => {
    api.getTask(taskPath).then((d) => setItems(d.sessions)).catch(() => setItems([]));
  }, [taskPath]);
  if (!items || items.length === 0) return null;
  const indent = 10 + depth * 14;
  return (
    <div>
      {items.map((s) => (
        <div
          key={s.cc_session_id}
          onClick={() => void loadHistorySession(s.cc_session_id)}
          style={{
            padding: "3px 8px", paddingLeft: indent + 14,
            cursor: "pointer", color: "var(--text)",
            fontSize: 11, display: "flex", alignItems: "center", gap: 4,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          <span>💬</span>
          <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {s.note || s.cc_session_id.slice(0, 8)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── 新建任务弹层 ─────────────────────────────────────────────────────────

function CreateTaskModal({ parentPath, defaultKind, onClose }: {
  parentPath: string;
  defaultKind: TaskKind;
  onClose: () => void;
}) {
  const createTask = useWorkspaceStore((s) => s.createTask);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [kind, setKind] = useState<TaskKind>(defaultKind);
  const [submitting, setSubmitting] = useState(false);

  async function handleCreate() {
    if (!name.trim() || submitting) return;
    setSubmitting(true);
    try {
      await createTask(name.trim(), kind, desc.trim(), parentPath);
      onClose();
    } catch (e) {
      alert(`创建失败：${String(e)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)", zIndex: 100 }} />
      <div
        style={{
          position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
          zIndex: 101, width: 380,
          background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8,
          boxShadow: "var(--shadow)", padding: 16,
        }}
      >
        <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "var(--text)" }}>
          {parentPath ? `在「${parentPath}」下新建` : "新建顶级任务"}
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <label style={{ fontSize: 11, color: "var(--text-dim)" }}>
            类型
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as TaskKind)}
              disabled={parentPath === ""}
              style={{ display: "block", marginTop: 4, width: "100%", padding: "5px 8px", border: "1px solid var(--border)", borderRadius: 4, fontSize: 13, color: "var(--text)", background: "var(--panel)" }}
            >
              <option value="poi">POI（顶级主题）</option>
              <option value="gameplay">玩法</option>
              <option value="prop">物件</option>
            </select>
            {parentPath === "" && <span style={{ display: "block", fontSize: 10, marginTop: 2, color: "var(--text-faint)" }}>顶级只能是 POI</span>}
          </label>
          <label style={{ fontSize: 11, color: "var(--text-dim)" }}>
            名称
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              placeholder="例：黑帮大宅 / 主线烘焙模式 / 可交互抽屉柜"
              onKeyDown={(e) => { if (e.key === "Enter") void handleCreate(); }}
              style={{ display: "block", marginTop: 4, width: "100%", padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 4, fontSize: 13, color: "var(--text)", background: "var(--panel)" }}
            />
          </label>
          <label style={{ fontSize: 11, color: "var(--text-dim)" }}>
            简介（可选）
            <textarea
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="一句话描述这个任务"
              rows={2}
              style={{ display: "block", marginTop: 4, width: "100%", padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 4, fontSize: 12, color: "var(--text)", background: "var(--panel)", resize: "vertical", fontFamily: "var(--sans)" }}
            />
          </label>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
          <button onClick={onClose} disabled={submitting} style={{ padding: "6px 14px", border: "1px solid var(--border)", borderRadius: 4, background: "var(--panel)", color: "var(--text)", cursor: "pointer", fontSize: 13 }}>取消</button>
          <button onClick={() => void handleCreate()} disabled={submitting || !name.trim()} style={{ padding: "6px 14px", border: "none", borderRadius: 4, background: "var(--accent)", color: "#fff", cursor: name.trim() ? "pointer" : "not-allowed", fontSize: 13, opacity: name.trim() && !submitting ? 1 : 0.5 }}>
            {submitting ? "创建中…" : "创建"}
          </button>
        </div>
      </div>
    </>
  );
}

// ── 「导入现有」菜单 ───────────────────────────────────────────────────

function ImportMenu({ onDone }: { onDone: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function runImportSpecs() {
    if (busy) return;
    setBusy(true);
    setOpen(false);
    try {
      const r = await api.importSpecs();
      const created = r.created_tasks.length;
      const imported = r.imported_specs.length;
      const skipped = r.skipped.length;
      await onDone();
      alert(`✅ 导入 specs 完成\n· 新建 ${created} 个任务\n· 归档 ${imported} 个 spec\n${skipped > 0 ? `· 跳过 ${skipped}（已存在）` : ""}`);
    } catch (e) {
      alert(`导入失败：${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function runImportDocs() {
    if (busy) return;
    setBusy(true);
    setOpen(false);
    try {
      const r = await api.importDocs();
      const imported = r.imported_docs.length;
      const skipped = r.skipped.length;
      const matched = r.imported_docs.filter((d) => d.task_path !== "unsorted").length;
      const unsorted = imported - matched;
      await onDone();
      alert(`✅ 导入 docs 完成\n· 自动匹配到任务 ${matched} 个\n· 未匹配进 unsorted ${unsorted} 个\n${skipped > 0 ? `· 跳过 ${skipped}（已存在）` : ""}`);
    } catch (e) {
      alert(`导入失败：${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <span style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(!open)}
        disabled={busy}
        title="把现有 specs/ 或 docs/ 文件归档到 workspace"
        style={{
          padding: "3px 8px", fontSize: 11,
          border: "1px solid var(--border)", borderRadius: 3,
          background: "var(--panel)", color: "var(--text)", cursor: "pointer",
          opacity: busy ? 0.6 : 1,
        }}
      >
        {busy ? "处理中…" : "📥 导入"}
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 60 }} />
          <div
            style={{
              position: "absolute", right: 0, top: "calc(100% + 4px)",
              zIndex: 61, minWidth: 200,
              background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 4,
              boxShadow: "var(--shadow)", padding: "4px 0", fontSize: 12,
            }}
          >
            <button
              onClick={() => void runImportSpecs()}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 12px", border: "none", background: "transparent", color: "var(--text)", cursor: "pointer", fontSize: 12 }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              从 <code style={{ fontFamily: "var(--mono)", fontSize: 11 }}>specs/</code> 归档
              <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 2 }}>按 level_id 聚类成 POI</div>
            </button>
            <button
              onClick={() => void runImportDocs()}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 12px", border: "none", background: "transparent", color: "var(--text)", cursor: "pointer", fontSize: 12 }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              从 <code style={{ fontFamily: "var(--mono)", fontSize: 11 }}>docs/</code> 归档
              <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 2 }}>按文件名匹配任务，未匹配进 unsorted</div>
            </button>
          </div>
        </>
      )}
    </span>
  );
}
