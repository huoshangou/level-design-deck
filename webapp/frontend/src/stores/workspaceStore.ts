// Workspace state：树缓存 + 展开折叠状态 + 加载状态。

import { create } from "zustand";
import { api } from "../api/client";
import type { TaskKind, WorkspaceTask, WorkspaceTree } from "../api/client";

type WorkspaceState = {
  tree: WorkspaceTree | null;
  loading: boolean;
  expanded: Set<string>;  // path 集合
  error: string | null;

  refresh: () => Promise<void>;
  toggleExpand: (path: string) => void;
  isExpanded: (path: string) => boolean;
  createTask: (name: string, kind: TaskKind, desc?: string, parent_path?: string) => Promise<void>;
  deleteTask: (path: string) => Promise<void>;
  linkDoc: (task_path: string, src_filename: string, move?: boolean) => Promise<void>;
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  tree: null,
  loading: false,
  expanded: new Set<string>(),
  error: null,

  refresh: async () => {
    set({ loading: true, error: null });
    try {
      const tree = await api.getWorkspace();
      // 首次加载自动展开所有顶级
      set((s) => {
        if (s.expanded.size === 0 && tree.tasks.length > 0) {
          const next = new Set(s.expanded);
          tree.tasks.forEach((t) => next.add(t.path));
          return { tree, loading: false, expanded: next };
        }
        return { tree, loading: false };
      });
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },

  toggleExpand: (path) => {
    set((s) => {
      const next = new Set(s.expanded);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return { expanded: next };
    });
  },

  isExpanded: (path) => get().expanded.has(path),

  createTask: async (name, kind, desc = "", parent_path = "") => {
    await api.createTask({ name, kind, desc, parent_path });
    // 自动展开父节点 + 自身
    if (parent_path) {
      set((s) => {
        const next = new Set(s.expanded);
        next.add(parent_path);
        return { expanded: next };
      });
    }
    await get().refresh();
  },

  deleteTask: async (path) => {
    await api.deleteTask(path);
    set((s) => {
      const next = new Set(s.expanded);
      next.delete(path);
      return { expanded: next };
    });
    await get().refresh();
  },

  linkDoc: async (task_path, src_filename, move = true) => {
    await api.linkDocToTask(task_path, src_filename, move);
    await get().refresh();
  },
}));

// 找树里某个 path 对应的 task（递归）
export function findTask(tasks: WorkspaceTask[], path: string): WorkspaceTask | null {
  for (const t of tasks) {
    if (t.path === path) return t;
    const found = findTask(t.children, path);
    if (found) return found;
  }
  return null;
}
