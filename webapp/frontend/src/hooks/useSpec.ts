// Spec / module schema 数据 hook，把 TanStack Query 与 editorStore 联动起来。

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { api } from "../api/client";
import { useEditorStore } from "../stores/editorStore";

export function useSpecList() {
  return useQuery({
    queryKey: ["specs"],
    queryFn: () => api.listSpecs(),
  });
}

export function useSpec(spec_id: string | null) {
  const loadContent = useEditorStore((s) => s.loadContent);
  const q = useQuery({
    queryKey: ["spec", spec_id],
    queryFn: () => api.getSpec(spec_id!),
    enabled: !!spec_id,
  });
  useEffect(() => {
    if (q.data) loadContent(q.data.content);
  }, [q.data, loadContent]);
  return q;
}

export function useModuleSchema(module: string | null) {
  return useQuery({
    queryKey: ["module-schema", module],
    queryFn: () => api.getModuleSchema(module!),
    enabled: !!module,
  });
}
