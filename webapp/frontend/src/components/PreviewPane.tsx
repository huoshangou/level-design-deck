type Props = {
  specId: string | null;
  refreshKey: number; // 改变这个值强制 iframe 重新加载
};

export default function PreviewPane({ specId, refreshKey }: Props) {
  if (!specId) {
    return (
      <div style={{ padding: 16, color: "var(--text-faint)", fontSize: 12 }}>
        无 spec 选中
      </div>
    );
  }
  const src = `/outputs/${specId}.html?v=${refreshKey}`;
  return (
    <iframe
      title={`preview-${specId}`}
      src={src}
      style={{ width: "100%", height: "100%", border: "none", background: "#fff" }}
    />
  );
}
