#!/usr/bin/env python3
"""
template_diff.py

把 spec 字段 vs work_docs_extract.json 的 poi_lighting_fields 做 diff，
标 MISSING (work_docs 有 spec 没有) / EXTRA (spec 有 work_docs 没提及) / MAPPED。

M1 范围：仅 lighting 范围。

使用：
  python3 tools/template_diff.py specs/demo_lighting_req.spec.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORK_DOCS = PROJECT_ROOT / "reference" / "work_docs_extract.json"
DEFAULT_TEMPLATE_FIELDS = PROJECT_ROOT / "reference" / "template_fields.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / ".diff.json"

# spec schema 字段路径 → work_docs poi_lighting_fields 字段名 映射
# M1 硬编码；M2 考虑挪到 schema 里 x-work-doc-field 元数据
SPEC_TO_WORKDOC_LIGHTING = {
    "map_constraint":               "地图收束_环境光",
    "level_constraint":             "关卡收束_常亮指引光",
    "mission_constraint":           "任务收束_任务流程灯光",
    "concept_art.ambient_only":     "夜景光效原画效果图_环境光版",
    "concept_art.with_mission":     "夜景光效原画效果图_任务灯光版",
    "position_notes":               "夜景光效位置说明",
    "ambience_refs":                "灯光氛围参考",
}


def get_spec_paths(spec, prefix=""):
    """返回 spec 中所有 top-level + 1 层嵌套的 leaf paths（按需）。
    M1 不深入 array items 内部，仅看顶层 + concept_art 子段。"""
    paths = set()
    if not isinstance(spec, dict):
        return paths
    for key, value in spec.items():
        path = f"{prefix}.{key}" if prefix else key
        paths.add(path)
        # 只对 concept_art 这一层展开（因为映射里有它的子段）
        if path == "concept_art" and isinstance(value, dict):
            for sub_key in value:
                paths.add(f"{path}.{sub_key}")
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="spec JSON 路径")
    parser.add_argument("--work-docs", type=Path, default=DEFAULT_WORK_DOCS)
    parser.add_argument("--template-fields", type=Path, default=DEFAULT_TEMPLATE_FIELDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.spec.exists():
        sys.exit(f"ERROR: spec not found: {args.spec}")
    if not args.work_docs.exists():
        sys.exit(f"ERROR: work_docs not found: {args.work_docs}")
    if not args.template_fields.exists():
        sys.exit(f"ERROR: template_fields not found: {args.template_fields}")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    # M3.2: 图状 module 走跳过分支（template_fields.json 是字段填空型 derived from gameplay_template.html，
    # 对图状 spec 无映射意义，强行套是反污染失误）。[来源: 第一原理推导]
    spec_id = spec.get("meta", {}).get("spec_id", "")
    SKIP_PREFIXES = {
        "bubble_diagram_": "graph-type module (nodes/edges, not field-clipboard)",
        "spatial_layout_": "geometry/external-tool module (LevelCraft 2D export, not field-clipboard)",
    }
    skip_reason = next((r for p, r in SKIP_PREFIXES.items() if spec_id.startswith(p)), None)
    if skip_reason:
        payload = {
            "diffed_at": datetime.now(timezone.utc).isoformat(),
            "spec_path": str(args.spec),
            "scope": skip_reason,
            "stats": {"mapped": 0, "missing": 0, "extra": 0},
            "mapped": [], "missing": [], "extra": [],
            "rationale": f"{skip_reason}; template_fields.json/work_docs_extract.json are field-clipboard derived. No mapping applicable. [来源: 第一原理推导]",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"mapped=0 missing=0 extra=0 (skipped: {skip_reason})")
        print(f"OK: diff written to {args.output}")
        sys.exit(0)

    work_docs = json.loads(args.work_docs.read_text(encoding="utf-8"))
    template_fields = json.loads(args.template_fields.read_text(encoding="utf-8"))

    spec_paths = get_spec_paths(spec)
    workdoc_lighting_names = {f["name"] for f in work_docs.get("poi_lighting_fields", [])}

    mapped = []
    missing = []
    extra = []

    # 检查映射表覆盖：spec 中映射表的 path 是否都存在
    for spec_path, workdoc_name in SPEC_TO_WORKDOC_LIGHTING.items():
        in_spec = spec_path in spec_paths
        in_workdoc = workdoc_name in workdoc_lighting_names
        if in_spec and in_workdoc:
            mapped.append({"spec_path": spec_path, "workdoc_name": workdoc_name})
        elif in_workdoc and not in_spec:
            missing.append({
                "workdoc_name": workdoc_name,
                "expected_spec_path": spec_path,
                "msg": f"work_docs 定义了字段 '{workdoc_name}'，spec 应在 '{spec_path}' 提供"
            })
        elif in_spec and not in_workdoc:
            extra.append({
                "spec_path": spec_path,
                "msg": f"spec 提供了 '{spec_path}'（映射到 '{workdoc_name}'），但 work_docs 未定义此字段"
            })

    # 检查映射表外的 spec 字段（schema 设计的非 lighting 元字段，如 meta）
    mapped_spec_paths = set(SPEC_TO_WORKDOC_LIGHTING.keys())
    for sp in spec_paths:
        if sp in mapped_spec_paths:
            continue
        # 已知非 lighting 字段：meta 及其子项
        if sp == "meta" or sp.startswith("meta."):
            continue
        # concept_art 顶层（其子项 ambient_only/with_mission 已映射）
        if sp == "concept_art":
            continue
        # 其他 → 视为 EXTRA（schema 多设计了字段）
        extra.append({
            "spec_path": sp,
            "msg": f"spec 提供 '{sp}'，不在映射表也不是 meta —— 检查是否 schema 设计冗余"
        })

    # 检查 work_docs 中映射表外的 lighting 字段（work_docs 出现新字段而映射表没跟上）
    mapped_workdoc_names = set(SPEC_TO_WORKDOC_LIGHTING.values())
    for name in workdoc_lighting_names:
        if name not in mapped_workdoc_names:
            missing.append({
                "workdoc_name": name,
                "expected_spec_path": "(未映射)",
                "msg": f"work_docs 定义了 '{name}'，但映射表未涵盖 —— schema 可能漏字段"
            })

    # 玩法 template 一致性检查
    gameplay_check = None
    template_field_names = {f["name"] for f in template_fields.get("fields", [])}
    if "light_requirement" in template_field_names:
        gameplay_check = {
            "status": "expected",
            "msg": "玩法 template 含 'light_requirement' (rich_editor 自由文本)，"
                   "POI lighting spec 是结构化 source of truth；玩法侧只需声明 N/A 或留空"
        }

    payload = {
        "diffed_at": datetime.now(timezone.utc).isoformat(),
        "spec_path": str(args.spec),
        "scope": "lighting only (M1)",
        "stats": {
            "mapped": len(mapped),
            "missing": len(missing),
            "extra": len(extra),
        },
        "mapped": mapped,
        "missing": missing,
        "extra": extra,
        "gameplay_consistency": gameplay_check,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"mapped={len(mapped)} missing={len(missing)} extra={len(extra)}")
    if not args.quiet:
        for m in missing:
            print(f"  [MISSING] {m['workdoc_name']}: {m['msg']}")
        for e in extra:
            print(f"  [EXTRA]   {e['spec_path']}: {e['msg']}")
        if gameplay_check:
            print(f"  [INFO]    {gameplay_check['msg']}")
    print(f"OK: diff written to {args.output}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
