import type { SpecInfo } from "../api/types";

type Props = {
  specs: SpecInfo[];
  currentId: string | null;
  onSelect: (id: string) => void;
};

export default function SpecPicker({ specs, currentId, onSelect }: Props) {
  // 按 level_id 分组（null/空归到「（无 level_id）」）
  const groups = new Map<string, SpecInfo[]>();
  for (const s of specs) {
    const key = s.level_id ?? "（无 level_id）";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(s);
  }
  const groupKeys = Array.from(groups.keys()).sort();

  return (
    <select
      value={currentId ?? ""}
      onChange={(e) => onSelect(e.target.value)}
      style={{
        padding: "4px 8px",
        fontSize: 12,
        border: "1px solid var(--border)",
        borderRadius: 3,
        background: "var(--panel)",
        minWidth: 320,
      }}
    >
      <option value="">— 选择 spec —</option>
      {groupKeys.map((g) => (
        <optgroup key={g} label={g}>
          {groups.get(g)!.map((s) => (
            <option key={s.id} value={s.id}>
              {s.id}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
