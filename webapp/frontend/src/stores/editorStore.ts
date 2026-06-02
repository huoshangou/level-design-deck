// 编辑器 client-side state：当前选中 spec、本地编辑副本、dirty 标记。
// Server state（spec / check / module list）由 TanStack Query 管理，不进这里。

import { create } from "zustand";
import { setByPath } from "../components/form/pathUtils";
import { useChatStore } from "./chatStore";

type EditorState = {
  currentSpecId: string | null;
  localContent: Record<string, unknown> | null;
  dirty: boolean;
  toast: { kind: "ok" | "err"; msg: string } | null;
  docTemplateUrl: string | null;
  docTemplateLabel: string | null;
  _specReloadTrigger: number;

  selectSpec: (id: string | null) => void;
  loadContent: (content: Record<string, unknown>) => void;
  updateField: (path: string, value: unknown) => void;
  markClean: () => void;
  showToast: (kind: "ok" | "err", msg: string) => void;
  clearToast: () => void;
  openDocTemplate: (url: string, label: string) => void;
  closeDocTemplate: () => void;
  triggerSpecReload: () => void;
};

export const useEditorStore = create<EditorState>((set, get) => ({
  currentSpecId: null,
  localContent: null,
  dirty: false,
  toast: null,
  docTemplateUrl: null,
  docTemplateLabel: null,
  _specReloadTrigger: 0,

  selectSpec: (id) => set({ currentSpecId: id, localContent: null, dirty: false }),
  loadContent: (content) => set({ localContent: content, dirty: false }),
  updateField: (path, value) => {
    const cur = get().localContent;
    if (!cur) return;
    try {
      set({ localContent: setByPath(cur, path, value), dirty: true });
    } catch (e) {
      set({ toast: { kind: "err", msg: String(e) } });
    }
  },
  markClean: () => set({ dirty: false }),
  showToast: (kind, msg) => set({ toast: { kind, msg } }),
  clearToast: () => set({ toast: null }),
  openDocTemplate: (url, label) => {
    set({ docTemplateUrl: url, docTemplateLabel: label });
    // 从 label 推断 kind（label 由 Topbar 构造，如"玩法设计 模板 v1.5"）
    const kind = label.includes("玩法") ? "gameplay" : label.includes("物件") ? "prop" : "unknown";
    useChatStore.getState().triggerDocFill(kind, label);
  },
  closeDocTemplate: () => set({ docTemplateUrl: null, docTemplateLabel: null }),
  triggerSpecReload: () => set((s) => ({ _specReloadTrigger: s._specReloadTrigger + 1 })),
}));
