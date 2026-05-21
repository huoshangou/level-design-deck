// 「👤 我」按钮 + 设计者配置弹窗。
// 第一次没填时按钮显示「👤 未设置」橙色提示；填了显示设计者中文名。

import { useEffect, useState } from "react";
import { api, type DesignerProfile } from "../../api/client";

const EMPTY_PROFILE: DesignerProfile = {
  designer_cn: "",
  designer_en_short: "",
  designer_full_en: "",
  notes: "",
};

export default function ProfileButton() {
  const [profile, setProfile] = useState<DesignerProfile | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    api.getProfile().then(setProfile).catch(() => setProfile(EMPTY_PROFILE));
  }, []);

  const isEmpty = !profile?.designer_cn && !profile?.designer_en_short;
  const label = isEmpty
    ? "👤 未设置"
    : `👤 ${profile?.designer_cn || profile?.designer_en_short}`;

  return (
    <>
      <button
        onClick={() => setModalOpen(true)}
        title={isEmpty ? "设置一次设计者信息，之后 AI 自动署名" : `点击修改 (${profile?.designer_en_short})`}
        style={{
          padding: "3px 8px",
          fontSize: 11,
          border: `1px solid ${isEmpty ? "var(--review)" : "var(--border)"}`,
          borderRadius: 3,
          background: isEmpty ? "var(--review-bg)" : "var(--panel)",
          color: isEmpty ? "var(--review)" : "var(--text)",
          cursor: "pointer",
          fontWeight: isEmpty ? 600 : 400,
        }}
      >
        {label}
      </button>
      {modalOpen && (
        <ProfileModal
          initial={profile ?? EMPTY_PROFILE}
          onClose={() => setModalOpen(false)}
          onSaved={(p) => { setProfile(p); setModalOpen(false); }}
        />
      )}
    </>
  );
}

function ProfileModal({ initial, onClose, onSaved }: {
  initial: DesignerProfile;
  onClose: () => void;
  onSaved: (p: DesignerProfile) => void;
}) {
  const [cn, setCn] = useState(initial.designer_cn);
  const [enShort, setEnShort] = useState(initial.designer_en_short);
  const [enFull, setEnFull] = useState(initial.designer_full_en);
  const [notes, setNotes] = useState(initial.notes);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (saving) return;
    setSaving(true);
    try {
      const saved = await api.updateProfile({
        designer_cn: cn.trim(),
        designer_en_short: enShort.trim(),
        designer_full_en: enFull.trim(),
        notes: notes.trim(),
      });
      onSaved(saved);
    } catch (e) {
      alert(`保存失败：${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)", zIndex: 100 }} />
      <div
        style={{
          position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
          zIndex: 101, width: 400,
          background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8,
          boxShadow: "var(--shadow)", padding: 18,
          fontFamily: "var(--sans)", color: "var(--text)",
        }}
      >
        <h3 style={{ margin: "0 0 4px", fontSize: 14 }}>👤 设计者信息</h3>
        <p style={{ margin: "0 0 14px", fontSize: 11, color: "var(--text-dim)", lineHeight: 1.5 }}>
          填一次，之后每次 chat 时 AI 会自动用你的名字署名 + 生成资产命名缩写。<br/>
          如果你公司用名和个人 Claude 配置不一样（比如 Steve / 芬里尔），填公司的就行。
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Field label="中文名 *" hint="AI 写文档时的署名（例：芬里尔）" value={cn} onChange={setCn} placeholder="芬里尔" autoFocus />
          <Field label="英文缩写 *" hint="资产命名 / 文件名用（例：FNR）" value={enShort} onChange={setEnShort} placeholder="FNR" />
          <Field label="英文全名" hint="可选" value={enFull} onChange={setEnFull} placeholder="Fenrir Steve" />
          <Field label="备注" hint="可选；给 AI 看的人物 context，比如「我主攻关卡设计，会自己做 demo」" value={notes} onChange={setNotes} placeholder="可选" rows={2} />
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
          <button onClick={onClose} disabled={saving} style={{ padding: "6px 14px", border: "1px solid var(--border)", borderRadius: 4, background: "var(--panel)", color: "var(--text)", cursor: "pointer", fontSize: 13 }}>取消</button>
          <button
            onClick={() => void handleSave()}
            disabled={saving || (!cn.trim() && !enShort.trim())}
            style={{
              padding: "6px 14px", border: "none", borderRadius: 4,
              background: "var(--accent)", color: "#fff",
              cursor: (cn.trim() || enShort.trim()) ? "pointer" : "not-allowed",
              fontSize: 13,
              opacity: ((cn.trim() || enShort.trim()) && !saving) ? 1 : 0.5,
            }}
          >
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </>
  );
}

function Field({ label, hint, value, onChange, placeholder, autoFocus, rows }: {
  label: string;
  hint?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  rows?: number;
}) {
  const sharedStyle: React.CSSProperties = {
    display: "block", marginTop: 3, width: "100%",
    padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 4,
    fontSize: 13, color: "var(--text)", background: "var(--panel)",
    fontFamily: "var(--sans)",
  };
  return (
    <label style={{ fontSize: 11, color: "var(--text-dim)" }}>
      {label}
      {hint && <span style={{ color: "var(--text-faint)", marginLeft: 6 }}>· {hint}</span>}
      {rows ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={rows} style={{ ...sharedStyle, resize: "vertical" }} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} autoFocus={autoFocus} style={sharedStyle} />
      )}
    </label>
  );
}
