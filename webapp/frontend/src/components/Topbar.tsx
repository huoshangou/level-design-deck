import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useEditorStore } from "../stores/editorStore";
import { useSpecList } from "../hooks/useSpec";
import SpecPicker from "./SpecPicker";

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
      <Btn onClick={onToggleChat}>{chatOpen ? "💬▶" : "◀💬"}</Btn>
    </header>
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
