// 合并 mechanical_check + template_diff + cross_check 为统一 Alert 列表给 sidebar 用。

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "../api/client";
import type { Alert } from "../api/types";

export function useChecks(spec_id: string | null, level_id: string | null) {
  const mech = useQuery({
    queryKey: ["check", spec_id],
    queryFn: () => api.checkSpec(spec_id!),
    enabled: !!spec_id,
  });
  const cross = useQuery({
    queryKey: ["cross", level_id],
    queryFn: () => api.crossCheck(level_id!),
    enabled: !!level_id,
  });

  const alerts = useMemo<Alert[]>(() => {
    const out: Alert[] = [];
    if (mech.data) {
      for (const e of mech.data.mechanical.errors) {
        out.push({ level: "ERROR", field_path: e.field_path, rule: e.rule, msg: e.msg, source: "mechanical" });
      }
      for (const r of mech.data.mechanical.reviews) {
        out.push({ level: "REVIEW", field_path: r.field_path, rule: r.rule, msg: r.msg, source: "mechanical" });
      }
      if (mech.data.template) {
        for (const m of mech.data.template.missing) {
          out.push({
            level: "MISSING",
            field_path: m.expected_spec_path ?? "",
            rule: "template_missing",
            msg: m.msg,
            source: "template",
          });
        }
        for (const e of mech.data.template.extra) {
          out.push({
            level: "EXTRA",
            field_path: e.spec_path ?? "",
            rule: "template_extra",
            msg: e.msg,
            source: "template",
          });
        }
      }
    }
    if (cross.data) {
      for (const e of cross.data.errors) {
        out.push({
          level: "ERROR",
          field_path: e.field_path,
          rule: e.rule,
          msg: `[cross] ${e.msg}`,
          source: "cross",
        });
      }
      for (const r of cross.data.reviews) {
        out.push({
          level: "REVIEW",
          field_path: r.field_path,
          rule: r.rule,
          msg: `[cross] ${r.msg}`,
          source: "cross",
        });
      }
    }
    return out;
  }, [mech.data, cross.data]);

  return {
    alerts,
    isLoading: mech.isLoading || cross.isLoading,
    refetch: async () => {
      await Promise.all([mech.refetch(), cross.refetch()]);
    },
    mechanicalStats: mech.data?.mechanical.stats,
    templateStats: mech.data?.template?.stats,
    crossStats: cross.data?.stats,
  };
}
