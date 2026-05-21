// 附件上传区：dropzone + picker + 附件 chip 列表。
// 独立子组件，避免 ChatSidebar 超 300 行。
import { useRef, useState } from "react";
import { useChatStore } from "../../stores/chatStore";
import type { AttachedFile } from "../../api/chat-types";

const WARN_BYTES = 5 * 1024 * 1024;   // > 5MB 黄色警告

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
}

function FileChip({ file, onRemove }: { file: AttachedFile; onRemove: () => void }) {
  const isBinary = file.kind === "binary";
  const isLarge = file.size_bytes > WARN_BYTES;
  const sizeStr = fmtSize(file.size_bytes);
  const bgColor = isBinary
    ? "rgba(239,68,68,0.08)"
    : isLarge
    ? "var(--review-bg)"
    : "var(--section-bg)";
  const borderColor = isBinary ? "var(--error)" : isLarge ? "var(--review)" : "var(--border)";
  const textColor = isBinary ? "var(--error)" : "var(--text)";
  const title = isBinary
    ? "cc 读不了二进制文件"
    : isLarge
    ? `${sizeStr} 偏大，AI 处理时可能触发上下文限制；> 20MB 会被服务端拒绝`
    : file.stored_path;
  return (
    <div
      title={title}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 6px",
        borderRadius: 4,
        fontSize: 11,
        background: bgColor,
        border: `1px solid ${borderColor}`,
        color: textColor,
        maxWidth: "100%",
        minWidth: 0,
      }}
    >
      <span style={{ flexShrink: 0 }}>📄</span>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
        {file.original_name}
      </span>
      <span style={{ color: isLarge ? "var(--review)" : "var(--text-faint)", flexShrink: 0, fontWeight: isLarge ? 600 : 400 }}>
        ({file.kind}, {sizeStr})
      </span>
      {isBinary && (
        <span style={{ color: "var(--error)", flexShrink: 0, fontSize: 10 }}>⚠</span>
      )}
      {isLarge && !isBinary && (
        <span style={{ color: "var(--review)", flexShrink: 0, fontSize: 10 }}>⚠</span>
      )}
      <button
        onClick={onRemove}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: "0 2px",
          color: "var(--text-faint)",
          fontSize: 12,
          lineHeight: 1,
          flexShrink: 0,
        }}
        title="删除附件"
      >
        ✕
      </button>
    </div>
  );
}

export default function AttachmentArea({ clientId }: { clientId: string | null }) {
  const { attachedFiles, uploadingFiles, uploadFile, removeAttachedFile } = useChatStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  async function handleFiles(files: FileList | File[]) {
    const arr = Array.from(files);
    for (const f of arr) {
      try {
        await uploadFile(f);
      } catch (e) {
        alert(`上传失败：${f.name}\n${String(e)}`);
      }
    }
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function onDragLeave() {
    setDragging(false);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) void handleFiles(e.dataTransfer.files);
  }

  function onPickerChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.length) void handleFiles(e.target.files);
    e.target.value = "";
  }

  const hasContent = attachedFiles.length > 0 || uploadingFiles.length > 0;

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      style={{
        borderTop: hasContent ? "1px solid var(--border)" : undefined,
        borderBottom: "1px solid var(--border)",
        background: dragging ? "rgba(99,102,241,0.06)" : "var(--panel)",
        padding: hasContent || dragging ? "6px 12px" : "0 12px",
        transition: "background 0.15s",
        flexShrink: 0,
      }}
    >
      {/* 上传中 */}
      {uploadingFiles.map((name) => (
        <div
          key={name}
          style={{
            fontSize: 11,
            color: "var(--text-faint)",
            padding: "2px 0",
          }}
        >
          ⏳ {name} 上传中…
        </div>
      ))}

      {/* 已上传 chip 列表 */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {attachedFiles.map((f) => (
          <FileChip
            key={f.file_id}
            file={f}
            onRemove={() => void removeAttachedFile(f.file_id)}
          />
        ))}
      </div>

      {/* 📎 picker 按钮 + dropzone hint */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: hasContent ? 4 : 0 }}>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={!clientId}
          style={{
            background: "none",
            border: "none",
            cursor: clientId ? "pointer" : "not-allowed",
            fontSize: 14,
            padding: "2px 4px",
            color: clientId ? "var(--text-dim)" : "var(--text-faint)",
          }}
          title="选择文件"
        >
          📎
        </button>
        {dragging && (
          <span style={{ fontSize: 11, color: "var(--accent)" }}>放开以上传</span>
        )}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          onChange={onPickerChange}
        />
      </div>
    </div>
  );
}
