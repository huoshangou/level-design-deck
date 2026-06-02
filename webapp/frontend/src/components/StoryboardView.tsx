import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { api } from "../api/client";

// ── Prompt composer (TS port of tools/storyboard_render.py PromptComposer) ──

const PLACEHOLDER_RE = /\{(style\.)?([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
const INHERIT_MAP: Record<string, string> = { lighting: "lighting_aesthetic" };

function composePrompt(panel: Record<string, unknown>, style: Record<string, unknown>, template: string): string {
  const styleVal = (field: string): string => {
    const v = style[field];
    if (v == null) return "";
    if (Array.isArray(v)) return v.filter(Boolean).join(", ");
    return String(v).trim();
  };
  const panelVal = (field: string): string => {
    let v = panel[field];
    if (v == null) v = "";
    const s = String(v).trim();
    if (!s && field in INHERIT_MAP) return styleVal(INHERIT_MAP[field]);
    return s;
  };
  const raw = template.replace(PLACEHOLDER_RE, (_m, isStyle: string | undefined, field: string) =>
    isStyle ? styleVal(field) : panelVal(field),
  );
  return raw
    .replace(/,\s*,/g, ",")
    .replace(/\s{2,}/g, " ")
    .replace(/,\s*$/, "")
    .trim()
    .replace(/^[, ]+|[, ]+$/g, "");
}

const DEFAULT_TEMPLATE =
  "{style.medium}, {style.art_direction}, {scene}, {subject_action}, {camera}, {lighting}, {mood}, {style.color_palette}, {style.quality_tags}";

// ── Types ──────────────────────────────────────────────────────────────

export interface StoryboardPanel {
  panel_id: string;
  beat_id: string;
  title: string;
  scene: string;
  subject_action: string;
  camera: string;
  lighting?: string;
  mood: string;
  player_intent?: string;
  player_feels?: string;
  gameplay_moment?: string;
  zone_id?: string;
  generated_prompt?: string;
  generated_image_url?: string;
  source_image_url?: string;
  [key: string]: unknown;
}

type BeatNode = {
  id: string;
  type: string;
  label: string;
  notes?: string;
  phase?: string;
  zone_id?: string;
};

type SourceMaterials = { script_text?: string; story_outline?: string } | null;
type LdNotes = { global_notes?: string; panel_notes?: Array<{ panel_id: string; note: string }> } | null;

interface Props {
  specId: string;
  levelId: string;
  panels: StoryboardPanel[];
  styleAnchor: Record<string, unknown>;
  promptTemplate: string;
  sourceMaterials: SourceMaterials;
  ldNotes: LdNotes;
  onChange: (path: string, value: unknown) => void;
  onPanelClick?: (idx: number) => void;
}

// ── Beat type badges ──────────────────────────────────────────────────

const BEAT_TYPE_STYLE: Record<string, { bg: string; label: string }> = {
  entry: { bg: "#e8f5e9", label: "入口" },
  exit: { bg: "#ffebee", label: "出口" },
  scene: { bg: "#e3f2fd", label: "场景" },
  combat: { bg: "#fce4ec", label: "战斗" },
  puzzle: { bg: "#fff3e0", label: "解谜" },
  dialogue: { bg: "#f3e5f5", label: "对话" },
  choice: { bg: "#fff8e1", label: "抉择" },
  cutscene: { bg: "#e0f2f1", label: "过场" },
};

// ── Component ──────────────────────────────────────────────────────────

type TabKey = "materials" | "mapping" | "panels";

export default function StoryboardView({
  specId,
  levelId,
  panels,
  styleAnchor,
  promptTemplate,
  sourceMaterials,
  ldNotes,
  onChange,
  onPanelClick,
}: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("panels");
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);
  const [uploadingPanel, setUploadingPanel] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingPanelRef = useRef<{ idx: number; panelId: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // beat mapping state
  const [beats, setBeats] = useState<BeatNode[]>([]);
  const [beatsLoading, setBeatsLoading] = useState(false);
  const [beatsError, setBeatsError] = useState<string | null>(null);
  const [selectedBeats, setSelectedBeats] = useState<Set<string>>(new Set());

  const template = promptTemplate || DEFAULT_TEMPLATE;
  const negPrompt = String(styleAnchor.negative_prompt ?? "").trim();

  const computedPrompts = useMemo(
    () => panels.map((p) => composePrompt(p as unknown as Record<string, unknown>, styleAnchor, template)),
    [panels, styleAnchor, template],
  );

  const existingBeatIds = useMemo(() => new Set(panels.map((p) => p.beat_id)), [panels]);

  // fetch beats when mapping tab opened
  useEffect(() => {
    if (activeTab !== "mapping" || !levelId) return;
    let cancelled = false;
    setBeatsLoading(true);
    setBeatsError(null);
    api.getBeats(levelId)
      .then((res) => { if (!cancelled) setBeats(res.nodes); })
      .catch((e) => { if (!cancelled) setBeatsError(String(e)); })
      .finally(() => { if (!cancelled) setBeatsLoading(false); });
    return () => { cancelled = true; };
  }, [activeTab, levelId]);

  const showCopyFeedback = useCallback((msg: string) => {
    setCopyFeedback(msg);
    setTimeout(() => setCopyFeedback(null), 1500);
  }, []);

  const copyAll = useCallback(() => {
    const text = panels.map((p, i) => {
      const lines = [
        `--- ${p.panel_id}: ${p.title} ---`,
        `[Prompt]`,
        computedPrompts[i],
        `[Negative]`,
        negPrompt,
      ];
      return lines.join("\n");
    }).join("\n\n");
    void navigator.clipboard.writeText(text);
    showCopyFeedback("已复制全部 prompt");
  }, [panels, computedPrompts, negPrompt, showCopyFeedback]);

  const copySingle = useCallback((idx: number) => {
    const text = `${computedPrompts[idx]}\n\n[Negative]\n${negPrompt}`;
    void navigator.clipboard.writeText(text);
    showCopyFeedback(`已复制 ${panels[idx].panel_id}`);
  }, [computedPrompts, negPrompt, panels, showCopyFeedback]);

  const exportTxt = useCallback(() => {
    const text = panels.map((p, i) => {
      return [
        `=== ${p.panel_id}: ${p.title} (beat: ${p.beat_id}) ===`,
        ``,
        `[Prompt]`,
        computedPrompts[i],
        ``,
        `[Negative]`,
        negPrompt,
        ``,
        `[设计意图] ${p.player_intent ?? ""}`,
        `[玩家体验] ${p.player_feels ?? ""}`,
        `[玩法时刻] ${p.gameplay_moment ?? ""}`,
      ].join("\n");
    }).join("\n\n" + "─".repeat(60) + "\n\n");

    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${specId}_prompts.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [panels, computedPrompts, negPrompt, specId]);

  const exportLdNotes = useCallback(() => {
    const globalNotes = ldNotes?.global_notes?.trim() || "(无)";
    const panelNotesList = ldNotes?.panel_notes ?? [];
    const today = new Date().toISOString().slice(0, 10);
    const lines = [
      `# LD 调整建议 — ${specId}`,
      `日期: ${today}`,
      ``,
      `## 整体建议`,
      globalNotes,
      ``,
      `## 逐帧备注`,
    ];
    if (panelNotesList.length === 0) {
      lines.push("(无逐帧备注)");
    } else {
      for (const pn of panelNotesList) {
        const panel = panels.find((p) => p.panel_id === pn.panel_id);
        const title = panel?.title ?? "";
        const beatId = panel?.beat_id ?? "";
        lines.push(`### ${pn.panel_id}: ${title} (beat: ${beatId})`);
        lines.push(pn.note);
        lines.push("");
      }
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${specId}_ld_notes.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [ldNotes, panels, specId]);

  const triggerUpload = useCallback((idx: number, panelId: string) => {
    pendingPanelRef.current = { idx, panelId };
    fileInputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const pending = pendingPanelRef.current;
    if (!file || !pending) return;
    e.target.value = "";

    setUploadingPanel(pending.panelId);
    try {
      const res = await api.uploadStoryboardImage(specId, pending.panelId, file);
      onChange(`panels[${pending.idx}].generated_image_url`, res.relative_path);
    } catch (err) {
      alert(`上传失败：${String(err)}`);
    } finally {
      setUploadingPanel(null);
    }
  }, [specId, onChange]);

  const handleDrop = useCallback(async (e: React.DragEvent, idx: number, panelId: string) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    setUploadingPanel(panelId);
    try {
      const res = await api.uploadStoryboardImage(specId, panelId, file);
      onChange(`panels[${idx}].generated_image_url`, res.relative_path);
    } catch (err) {
      alert(`上传失败：${String(err)}`);
    } finally {
      setUploadingPanel(null);
    }
  }, [specId, onChange]);

  const scrollToPanel = useCallback((idx: number) => {
    const el = scrollRef.current?.querySelector(`[data-panel-idx="${idx}"]`);
    el?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }, []);

  // ── source_materials helpers ──

  const updateSourceMaterial = useCallback((field: "script_text" | "story_outline", value: string) => {
    const current = sourceMaterials ?? {};
    onChange("source_materials", { ...current, [field]: value });
  }, [sourceMaterials, onChange]);

  // ── ld_notes helpers ──

  const updateGlobalNotes = useCallback((value: string) => {
    const current = ldNotes ?? {};
    onChange("ld_notes", { ...current, global_notes: value });
  }, [ldNotes, onChange]);

  const updatePanelNote = useCallback((panelId: string, note: string) => {
    const current = ldNotes ?? {};
    const existing = current.panel_notes ?? [];
    const idx = existing.findIndex((pn) => pn.panel_id === panelId);
    let updated;
    if (note.trim() === "") {
      updated = existing.filter((pn) => pn.panel_id !== panelId);
    } else if (idx >= 0) {
      updated = existing.map((pn, i) => i === idx ? { panel_id: panelId, note } : pn);
    } else {
      updated = [...existing, { panel_id: panelId, note }];
    }
    onChange("ld_notes", { ...current, panel_notes: updated });
  }, [ldNotes, onChange]);

  const getPanelNote = useCallback((panelId: string): string => {
    return ldNotes?.panel_notes?.find((pn) => pn.panel_id === panelId)?.note ?? "";
  }, [ldNotes]);

  // ── beat mapping: generate panel skeletons ──

  const generatePanelSkeletons = useCallback(() => {
    const newBeats = beats.filter((b) => selectedBeats.has(b.id) && !existingBeatIds.has(b.id));
    if (newBeats.length === 0) return;
    const startIdx = panels.length;
    const newPanels = newBeats.map((b, i) => ({
      panel_id: `p${String(startIdx + i + 1).padStart(2, "0")}`,
      beat_id: b.id,
      title: b.label,
      scene: "",
      subject_action: "",
      camera: "",
      mood: "",
      zone_id: b.zone_id ?? "",
    }));
    onChange("panels", [...panels, ...newPanels]);
    setSelectedBeats(new Set());
    showCopyFeedback(`已生成 ${newPanels.length} 个面板骨架`);
  }, [beats, selectedBeats, existingBeatIds, panels, onChange, showCopyFeedback]);

  const hasLdNotes = !!(ldNotes?.global_notes?.trim() || (ldNotes?.panel_notes && ldNotes.panel_notes.length > 0));

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* ── Tab Bar ── */}
      <div style={{
        display: "flex", alignItems: "center", gap: 0,
        padding: "0 12px",
        background: "var(--panel)",
        borderBottom: "1px solid var(--border)",
        flexShrink: 0,
      }}>
        {([
          ["materials", "素材导入"],
          ["mapping", "节点映射"],
          ["panels", "分镜面板"],
        ] as [TabKey, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            style={{
              padding: "8px 14px",
              fontSize: 11,
              fontWeight: activeTab === key ? 600 : 400,
              color: activeTab === key ? "var(--accent)" : "var(--text-dim)",
              background: "none",
              border: "none",
              borderBottom: activeTab === key ? "2px solid var(--accent)" : "2px solid transparent",
              cursor: "pointer",
              fontFamily: "var(--sans)",
            }}
          >
            {label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        {activeTab === "panels" && (
          <>
            <button onClick={copyAll} style={btnStyle} title="复制所有 panel 的 prompt + negative">
              批量复制 prompt
            </button>
            <button onClick={exportTxt} style={{ ...btnStyle, marginLeft: 4 }} title="导出为 .txt 文件">
              导出 .txt
            </button>
          </>
        )}
        <button
          onClick={exportLdNotes}
          style={{ ...btnStyle, marginLeft: 4, opacity: hasLdNotes ? 1 : 0.4 }}
          title={hasLdNotes ? "导出 LD 调整建议为 markdown" : "暂无 LD 建议"}
        >
          导出 LD 建议
        </button>
      </div>

      {/* ── Tab Content ── */}
      {activeTab === "materials" && (
        <MaterialsTab
          sourceMaterials={sourceMaterials}
          globalNotes={ldNotes?.global_notes ?? ""}
          onUpdateMaterial={updateSourceMaterial}
          onUpdateGlobalNotes={updateGlobalNotes}
        />
      )}

      {activeTab === "mapping" && (
        <MappingTab
          beats={beats}
          loading={beatsLoading}
          error={beatsError}
          existingBeatIds={existingBeatIds}
          selectedBeats={selectedBeats}
          onToggleBeat={(id) => {
            setSelectedBeats((prev) => {
              const next = new Set(prev);
              if (next.has(id)) next.delete(id); else next.add(id);
              return next;
            });
          }}
          onGenerate={generatePanelSkeletons}
          levelId={levelId}
        />
      )}

      {activeTab === "panels" && (
        <>
          {/* ── Panel Nav ── */}
          <div style={{
            display: "flex", gap: 4, padding: "4px 12px",
            background: "var(--surface)", borderBottom: "1px solid var(--border-faint)",
            flexShrink: 0, overflowX: "auto",
            alignItems: "center",
          }}>
            <span style={{ fontSize: 10, color: "var(--text-faint)", marginRight: 4 }}>序列：</span>
            {panels.map((p, i) => (
              <span key={p.panel_id} style={{ display: "inline-flex", alignItems: "center", gap: 2 }}>
                {i > 0 && <span style={{ color: "var(--text-faint)", fontSize: 9 }}>→</span>}
                <button
                  onClick={() => { scrollToPanel(i); onPanelClick?.(i); }}
                  style={{
                    padding: "2px 8px", fontSize: 10, border: "1px solid var(--border)",
                    borderRadius: 10, background: "var(--panel)", cursor: "pointer",
                    color: "var(--text)", fontFamily: "var(--mono)",
                  }}
                >
                  <b>{p.panel_id}</b> {p.title}
                </button>
              </span>
            ))}
          </div>

          {/* ── Cards Scroll Area ── */}
          <div
            ref={scrollRef}
            style={{
              flex: 1, overflowX: "auto", overflowY: "auto",
              display: "flex", gap: 16, padding: 16,
              alignItems: "flex-start",
              background: "var(--bg)",
            }}
          >
            {panels.map((panel, idx) => {
              const prompt = computedPrompts[idx];
              const isExpanded = expandedPrompt === panel.panel_id;
              const isUploading = uploadingPanel === panel.panel_id;
              const imgUrl = panel.generated_image_url || "";
              const panelNote = getPanelNote(panel.panel_id);

              return (
                <div
                  key={panel.panel_id}
                  data-panel-idx={idx}
                  onClick={() => onPanelClick?.(idx)}
                  style={{
                    minWidth: 340, maxWidth: 400, flexShrink: 0,
                    background: "var(--panel)", border: "1px solid var(--border)",
                    borderRadius: "var(--radius)", boxShadow: "var(--shadow-sm)",
                    display: "flex", flexDirection: "column", cursor: "pointer",
                    overflow: "hidden",
                  }}
                >
                  {/* Header */}
                  <div style={{
                    padding: "8px 12px",
                    borderBottom: "1px solid var(--border-faint)",
                    display: "flex", alignItems: "center", gap: 8,
                  }}>
                    <span style={{
                      fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-faint)",
                      padding: "1px 5px", background: "var(--surface)", borderRadius: 3,
                    }}>
                      {panel.panel_id}
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{panel.title}</span>
                    <span style={{
                      fontSize: 10, padding: "1px 6px", borderRadius: 8,
                      background: "var(--accent-bg)", color: "var(--accent)", fontFamily: "var(--mono)",
                    }}>
                      beat:{panel.beat_id}
                    </span>
                    {panel.zone_id && (
                      <span style={{
                        fontSize: 10, padding: "1px 6px", borderRadius: 8,
                        background: "var(--review-bg)", color: "var(--review)",
                      }}>
                        {panel.zone_id}
                      </span>
                    )}
                  </div>

                  {/* Image Frame (16:9) */}
                  <div
                    onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                    onDrop={(e) => void handleDrop(e, idx, panel.panel_id)}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!imgUrl) triggerUpload(idx, panel.panel_id);
                    }}
                    style={{
                      aspectRatio: "16 / 9",
                      background: imgUrl ? "var(--text)" : "linear-gradient(135deg, #f3ead4 0%, #e8dcb9 100%)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      position: "relative", overflow: "hidden",
                      cursor: imgUrl ? "default" : "pointer",
                      borderBottom: "1px solid var(--border-faint)",
                    }}
                  >
                    {imgUrl ? (
                      <>
                        <img
                          src={`/${imgUrl}`}
                          alt={panel.title}
                          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                        <button
                          onClick={(e) => { e.stopPropagation(); triggerUpload(idx, panel.panel_id); }}
                          style={{
                            position: "absolute", top: 6, right: 6,
                            padding: "3px 8px", fontSize: 10,
                            background: "rgba(0,0,0,0.6)", color: "#fff",
                            border: "none", borderRadius: 3, cursor: "pointer",
                          }}
                        >
                          替换图
                        </button>
                      </>
                    ) : (
                      <div style={{ textAlign: "center", color: "#a08a5e", fontFamily: "var(--mono)", fontSize: 11 }}>
                        {isUploading ? (
                          <div>上传中…</div>
                        ) : (
                          <>
                            <div style={{ fontSize: 20, opacity: 0.4, marginBottom: 4 }}>✎</div>
                            <div>拖入图片 / 点击上传</div>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Design Intent */}
                  <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border-faint)" }}>
                    <div style={{ fontSize: 9, fontWeight: 600, color: "var(--text-faint)", letterSpacing: 1, marginBottom: 4 }}>设计意图</div>
                    {panel.player_intent && <InfoRow label="玩家意图" value={panel.player_intent} />}
                    {panel.player_feels && <InfoRow label="玩家体验" value={panel.player_feels} />}
                    {panel.gameplay_moment && <InfoRow label="玩法时刻" value={panel.gameplay_moment} />}
                  </div>

                  {/* Prompt Section */}
                  <div style={{ padding: "8px 12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <span style={{ fontSize: 9, fontWeight: 600, color: "var(--text-faint)", letterSpacing: 1 }}>PROMPT</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); copySingle(idx); }}
                        style={smallBtnStyle}
                      >
                        复制
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setExpandedPrompt(isExpanded ? null : panel.panel_id); }}
                        style={smallBtnStyle}
                      >
                        {isExpanded ? "收起" : "展开"}
                      </button>
                    </div>
                    <div style={{
                      fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-dim)",
                      background: "var(--surface)", padding: "6px 8px", borderRadius: 3,
                      whiteSpace: isExpanded ? "pre-wrap" : "nowrap",
                      overflow: "hidden", textOverflow: isExpanded ? "unset" : "ellipsis",
                      maxHeight: isExpanded ? "none" : 36, lineHeight: 1.5,
                      wordBreak: "break-word",
                    }}>
                      {prompt || "(空)"}
                    </div>
                  </div>

                  {/* LD Panel Note */}
                  <div style={{ padding: "4px 12px 8px", borderTop: "1px solid var(--border-faint)" }}>
                    <div style={{ fontSize: 9, fontWeight: 600, color: "var(--text-faint)", letterSpacing: 1, marginBottom: 3 }}>LD 备注</div>
                    <textarea
                      value={panelNote}
                      onChange={(e) => { e.stopPropagation(); updatePanelNote(panel.panel_id, e.target.value); }}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="对该帧的大纲/剧本调整建议…"
                      rows={2}
                      style={{
                        width: "100%", resize: "vertical", fontSize: 11, lineHeight: 1.5,
                        fontFamily: "var(--sans)", padding: "4px 6px",
                        border: "1px solid var(--border-faint)", borderRadius: 3,
                        background: "var(--surface)", color: "var(--text)",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Copy feedback toast */}
      {copyFeedback && (
        <div style={{
          position: "fixed", bottom: 20, left: "50%", transform: "translateX(-50%)",
          padding: "6px 16px", fontSize: 12, color: "#fff",
          background: "var(--success)", borderRadius: 4,
          boxShadow: "var(--shadow)", zIndex: 200,
        }}>
          {copyFeedback}
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        style={{ display: "none" }}
        onChange={(e) => void handleFileSelected(e)}
      />
    </div>
  );
}

// ── MaterialsTab ──────────────────────────────────────────────────────

function MaterialsTab({
  sourceMaterials,
  globalNotes,
  onUpdateMaterial,
  onUpdateGlobalNotes,
}: {
  sourceMaterials: SourceMaterials;
  globalNotes: string;
  onUpdateMaterial: (field: "script_text" | "story_outline", value: string) => void;
  onUpdateGlobalNotes: (value: string) => void;
}) {
  return (
    <div style={{ flex: 1, overflow: "auto", padding: 16, background: "var(--bg)" }}>
      <div style={{ maxWidth: 800, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
        <TextAreaSection
          title="剧本文本"
          description="粘贴剧本原文或摘要。分镜设计时可随时切回查阅。"
          value={sourceMaterials?.script_text ?? ""}
          onChange={(v) => onUpdateMaterial("script_text", v)}
          placeholder="粘贴剧本原文、对白、场景描述…"
          rows={12}
        />
        <TextAreaSection
          title="故事大纲"
          description="故事结构、叙事节奏、关键事件节点。"
          value={sourceMaterials?.story_outline ?? ""}
          onChange={(v) => onUpdateMaterial("story_outline", v)}
          placeholder="粘贴故事大纲、幕结构、节点列表…"
          rows={10}
        />
        <TextAreaSection
          title="LD 整体建议"
          description="全局性的大纲/剧本调整建议，针对整体叙事节奏、结构问题。导出时作为 LD 建议的第一部分。"
          value={globalNotes}
          onChange={onUpdateGlobalNotes}
          placeholder="整体叙事节奏是否合理？是否需要调整幕结构？角色动机是否清晰？…"
          rows={6}
        />
      </div>
    </div>
  );
}

function TextAreaSection({ title, description, value, onChange, placeholder, rows }: {
  title: string;
  description: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  rows: number;
}) {
  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, color: "var(--text)" }}>{title}</div>
      <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 8 }}>{description}</div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        style={{
          width: "100%", resize: "vertical", fontSize: 12, lineHeight: 1.6,
          fontFamily: "var(--sans)", padding: "10px 12px",
          border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
          background: "var(--panel)", color: "var(--text)",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}

// ── MappingTab ─────────────────────────────────────────────────────────

function MappingTab({
  beats,
  loading,
  error,
  existingBeatIds,
  selectedBeats,
  onToggleBeat,
  onGenerate,
  levelId,
}: {
  beats: BeatNode[];
  loading: boolean;
  error: string | null;
  existingBeatIds: Set<string>;
  selectedBeats: Set<string>;
  onToggleBeat: (id: string) => void;
  onGenerate: () => void;
  levelId: string;
}) {
  const newCount = beats.filter((b) => selectedBeats.has(b.id) && !existingBeatIds.has(b.id)).length;

  // group beats by phase
  const phases = useMemo(() => {
    const map = new Map<string, BeatNode[]>();
    for (const b of beats) {
      const phase = b.phase || "(未分组)";
      if (!map.has(phase)) map.set(phase, []);
      map.get(phase)!.push(b);
    }
    return map;
  }, [beats]);

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-faint)" }}>
        加载 bubble_diagram 节点…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ flex: 1, padding: 24, color: "var(--text-faint)", textAlign: "center" }}>
        <div style={{ fontSize: 13, marginBottom: 8 }}>该关卡尚未创建流程图 (bubble_diagram)</div>
        <div style={{ fontSize: 11 }}>请先创建 bubble_diagram_{levelId} spec，再进行节点映射。</div>
      </div>
    );
  }

  if (beats.length === 0) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-faint)", fontSize: 12 }}>
        bubble_diagram 中没有节点
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflow: "auto", padding: 16, background: "var(--bg)" }}>
      <div style={{ maxWidth: 700, margin: "0 auto" }}>
        <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 12 }}>
          勾选需要分镜的关键节点，点击"生成面板骨架"自动创建 panel。已有 panel 的节点显示为已关联。
        </div>

        {Array.from(phases.entries()).map(([phase, nodes]) => (
          <div key={phase} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text-faint)", letterSpacing: 1, marginBottom: 6, textTransform: "uppercase" }}>
              {phase}
            </div>
            {nodes.map((b) => {
              const alreadyMapped = existingBeatIds.has(b.id);
              const isSelected = selectedBeats.has(b.id);
              const typeInfo = BEAT_TYPE_STYLE[b.type] ?? { bg: "#f5f5f5", label: b.type };

              return (
                <label
                  key={b.id}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: 8,
                    padding: "8px 10px", marginBottom: 4,
                    background: alreadyMapped ? "var(--surface)" : "var(--panel)",
                    border: "1px solid var(--border-faint)",
                    borderRadius: "var(--radius-sm)",
                    cursor: alreadyMapped ? "default" : "pointer",
                    opacity: alreadyMapped ? 0.6 : 1,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={alreadyMapped || isSelected}
                    disabled={alreadyMapped}
                    onChange={() => { if (!alreadyMapped) onToggleBeat(b.id); }}
                    style={{ marginTop: 2 }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                      <span style={{
                        fontSize: 10, padding: "1px 6px", borderRadius: 8,
                        background: typeInfo.bg, color: "#333", fontWeight: 500,
                      }}>
                        {typeInfo.label}
                      </span>
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{b.label}</span>
                      <span style={{ fontSize: 10, fontFamily: "var(--mono)", color: "var(--text-faint)" }}>{b.id}</span>
                      {alreadyMapped && (
                        <span style={{ fontSize: 9, color: "var(--success)", fontWeight: 500 }}>已关联</span>
                      )}
                    </div>
                    {b.notes && (
                      <div style={{ fontSize: 10, color: "var(--text-dim)", lineHeight: 1.4, marginTop: 2 }}>
                        {b.notes.length > 120 ? b.notes.slice(0, 120) + "…" : b.notes}
                      </div>
                    )}
                    {b.zone_id && (
                      <span style={{
                        fontSize: 9, padding: "1px 5px", borderRadius: 6, marginTop: 3, display: "inline-block",
                        background: "var(--review-bg)", color: "var(--review)",
                      }}>
                        {b.zone_id}
                      </span>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        ))}

        <div style={{
          position: "sticky", bottom: 0, padding: "12px 0",
          background: "var(--bg)", borderTop: "1px solid var(--border-faint)",
        }}>
          <button
            onClick={onGenerate}
            disabled={newCount === 0}
            style={{
              padding: "8px 20px", fontSize: 12, fontWeight: 600,
              border: "none", borderRadius: "var(--radius-sm)",
              background: newCount > 0 ? "var(--accent)" : "var(--border)",
              color: newCount > 0 ? "#fff" : "var(--text-faint)",
              cursor: newCount > 0 ? "pointer" : "default",
              fontFamily: "var(--sans)",
            }}
          >
            生成面板骨架 ({newCount})
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ fontSize: 11, lineHeight: 1.5, marginBottom: 2 }}>
      <span style={{ color: "var(--text-faint)", fontSize: 10, fontFamily: "var(--mono)", marginRight: 4 }}>{label}:</span>
      <span style={{ color: "var(--text-dim)" }}>{value}</span>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: 11,
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  background: "var(--panel)",
  color: "var(--text)",
  cursor: "pointer",
  fontFamily: "var(--sans)",
};

const smallBtnStyle: React.CSSProperties = {
  padding: "1px 6px", fontSize: 9, border: "1px solid var(--border)",
  borderRadius: 3, background: "var(--surface)", cursor: "pointer",
  color: "var(--text-dim)",
};
