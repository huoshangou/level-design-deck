// 编辑器 client-side state：当前选中 spec、本地编辑副本、dirty 标记。
// Server state（spec / check / module list）由 TanStack Query 管理，不进这里。

import { create } from "zustand";
import { setByPath } from "../components/form/pathUtils";

type EditorState = {
  currentSpecId: string | null;
  localContent: Record<string, unknown> | null;
  dirty: boolean;
  toast: { kind: "ok" | "err"; msg: string } | null;

  selectSpec: (id: string | null) => void;
  loadContent: (content: Record<string, unknown>) => void;
  updateField: (path: string, value: unknown) => void;
  markClean: () => void;
  showToast: (kind: "ok" | "err", msg: string) => void;
  clearToast: () => void;
};

export const useEditorStore = create<EditorState>((set, get) => ({
  currentSpecId: null,
  localContent: null,
  dirty: false,
  toast: null,

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
}));
