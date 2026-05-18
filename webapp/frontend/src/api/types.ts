// 与 backend Pydantic / dataclass response 对齐的 TS 类型。
// backend 路径: webapp/backend/api/*.py + backend/services/*.py

export type Health = {
  status: string;
  agent_backend: string;
  namespace_default: string;
  project_root: string;
};

export type SpecInfo = {
  id: string;
  module: string | null;
  level_id: string | null;
  mtime: number;
};

export type SpecRecord = {
  id: string;
  content: Record<string, unknown>;
  mtime: number;
  module: string | null;
  level_id: string | null;
};

export type SaveResult = {
  id: string;
  mtime: number;
};

export type ModuleInfo = {
  name: string;
  schema_path: string | null;
  demo_path: string | null;
  lvm_generated: boolean;
  spec_id_pattern: string | null;
};

export type MechanicalWarning = {
  level: "ERROR" | "REVIEW";
  field_path: string;
  rule: string;
  msg: string;
};

export type MechanicalResult = {
  errors: MechanicalWarning[];
  reviews: MechanicalWarning[];
  stats: { errors: number; reviews: number };
  module: string | null;
  schema_path: string;
};

export type TemplateDiffEntry = {
  spec_path?: string;
  workdoc_name?: string;
  expected_spec_path?: string;
  msg: string;
};

export type TemplateDiffResult = {
  diffed_at: string;
  spec_path: string;
  scope: string;
  stats: { mapped: number; missing: number; extra: number };
  mapped: Array<{ spec_path: string; workdoc_name: string }>;
  missing: TemplateDiffEntry[];
  extra: TemplateDiffEntry[];
  rationale?: string;
};

export type CheckResult = {
  mechanical: MechanicalResult;
  template: TemplateDiffResult | null;
};

export type CrossCheckWarning = {
  level: "ERROR" | "REVIEW";
  field_path: string;
  rule: string;
  msg: string;
};

export type CrossCheckResult = {
  level_id: string;
  spec_paths: string[];
  modules: string[];
  cross_checks_run: string[];
  errors: CrossCheckWarning[];
  reviews: CrossCheckWarning[];
  stats: { errors: number; reviews: number };
  warning?: string;
};

export type RenderResult = {
  spec_id: string;
  module: string;
  output_path: string;
  size_bytes: number;
};

export type RenderLevelResult = {
  level_id: string;
  output_path: string;
  modules: string[];
  rendered: string[];
};

export type RenderDeckResult = {
  level_id: string;
  output_path: string;
  size_bytes: number;
};

// 统一的 sidebar alert，合并 mechanical / template_diff / cross_check
export type Alert = {
  level: "ERROR" | "REVIEW" | "MISSING" | "EXTRA" | "INFO";
  field_path: string;     // 点击跳转用
  rule: string;
  msg: string;
  source: "mechanical" | "template" | "cross";
};
