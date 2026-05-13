#!/usr/bin/env python3
"""
cross_check.py

跨 spec 校验：同一 level_id 的多个 spec 之间的引用完整性检查。
不引入外部依赖（标准库 only）。

使用：
  python3 tools/cross_check.py --level-id my_level
  python3 tools/cross_check.py --specs specs/lighting_req_X.spec.json specs/spatial_layout_X.spec.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / ".cross_warnings.json"

# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class CrossValidator:
    def __init__(self):
        self.errors = []
        self.reviews = []

    def add_error(self, path, rule, msg):
        self.errors.append({"level": "ERROR", "field_path": path, "rule": rule, "msg": msg})

    def add_review(self, path, rule, msg):
        self.reviews.append({"level": "REVIEW", "field_path": path, "rule": rule, "msg": msg})

# ---------------------------------------------------------------------------
# Cross-check registry
# ---------------------------------------------------------------------------

CROSS_CHECKS = []

def register_cross_check(desc):
    def deco(f):
        CROSS_CHECKS.append((desc, f))
        return f
    return deco

def _get_spatial_labels(spatial: dict) -> set:
    """从 spatial_layout spec 提取所有非空 shape label 集合。"""
    labels = set()
    for s in spatial.get("layout", {}).get("shapes", []):
        if isinstance(s, dict):
            label = (s.get("label") or "").strip()
            if label:
                labels.add(label)
    return labels

def _check_zone_field(v, spatial_labels, items, field_path_prefix, id_key):
    """通用 zone ref 校验：遍历 items，取 id_key，不在 spatial_labels 则报 ERROR。"""
    sample = sorted(spatial_labels)[:10]
    tail = "..." if len(spatial_labels) > 10 else ""
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        zid = (item.get(id_key) or "").strip()
        if not zid:
            continue
        if zid not in spatial_labels:
            v.add_error(
                f"{field_path_prefix}[{i}].{id_key}",
                "cross_ref_integrity",
                f"{id_key} {zid!r} not in spatial_layout.shapes[].label "
                f"(available labels: {sample}{tail})",
            )


_ZONE_REF_RULES = [
    ("lighting_req.ambience_refs[].region_id ∈ spatial_layout.shapes[].label",
     "lighting_req", "ambience_refs", "region_id"),
    ("vfx_req.effects[].zone_id ∈ spatial_layout.shapes[].label",
     "vfx_req", "effects", "zone_id"),
    ("audio_req.ambient_sounds[].region_id ∈ spatial_layout.shapes[].label",
     "audio_req", "ambient_sounds", "region_id"),
    ("atmosphere_ref.zones[].zone_id ∈ spatial_layout.shapes[].label",
     "atmosphere_ref", "zones", "zone_id"),
    ("asset_list.assets[].ref_zone_id ∈ spatial_layout.shapes[].label",
     "asset_list", "assets", "ref_zone_id"),
]

def _make_zone_ref_check(module, collection, id_key):
    def fn(specs_by_module, v):
        spec = specs_by_module.get(module)
        spatial = specs_by_module.get("spatial_layout")
        if not spec or not spatial:
            return
        _check_zone_field(v, _get_spatial_labels(spatial),
                          spec.get(collection, []),
                          f"{module}.{collection}", id_key)
    return fn

for _desc, _mod, _col, _key in _ZONE_REF_RULES:
    register_cross_check(_desc)(_make_zone_ref_check(_mod, _col, _key))

@register_cross_check("bubble_diagram phase 命名汇总（REVIEW）")
def bubble_phase_summary(specs_by_module, v):
    bubble = specs_by_module.get("bubble_diagram")
    if not bubble:
        return
    phases = {n["phase"] for n in bubble.get("nodes", []) if isinstance(n, dict) and n.get("phase")}
    if phases:
        v.add_review("bubble_diagram.nodes[].phase", "bubble_phase_summary",
                     f"bubble_diagram phase 命名集合：{sorted(phases)}。请确认 phase 命名在整个 level 文档中一致。")

@register_cross_check("bubble_diagram nodes[].zone_id ∈ spatial_layout.shapes[].label")
def check_bubble_zone_ref(specs_by_module, v):
    bubble = specs_by_module.get("bubble_diagram")
    spatial = specs_by_module.get("spatial_layout")
    if not bubble or not spatial:
        return
    _check_zone_field(v, _get_spatial_labels(spatial),
                      bubble.get("nodes", []),
                      "bubble_diagram.nodes", "zone_id")

# ---------------------------------------------------------------------------
# Spec loading helpers
# ---------------------------------------------------------------------------

def load_spec(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(1)


def get_level_id(spec: dict, path: Path) -> str:
    """Try meta.level_id first, then extract from spec_id, then from filename."""
    meta = spec.get("meta", {})
    if meta.get("level_id"):
        return meta["level_id"].strip()
    spec_id = (meta.get("spec_id") or "").strip()
    if spec_id:
        # spec_id 形如 lighting_req_my_level → 去掉 module 前缀
        for module in sorted(_known_modules(), key=len, reverse=True):
            prefix = module + "_"
            if spec_id.startswith(prefix):
                return spec_id[len(prefix):]
    # fallback: filename without .spec.json
    stem = path.stem.replace(".spec", "")
    for module in sorted(_known_modules(), key=len, reverse=True):
        prefix = module + "_"
        if stem.startswith(prefix):
            return stem[len(prefix):]
    return stem


def _known_modules() -> list:
    schema_dir = PROJECT_ROOT / "schema"
    if schema_dir.exists():
        return [p.name[: -len(".schema.json")] for p in schema_dir.glob("*.schema.json")]
    return ["lighting_req", "spatial_layout", "bubble_diagram"]


def get_module(spec: dict, path: Path) -> str:
    """Extract module name from spec_id or filename."""
    meta = spec.get("meta", {})
    spec_id = (meta.get("spec_id") or "").strip()
    source = spec_id or path.stem.replace(".spec", "")
    for module in sorted(_known_modules(), key=len, reverse=True):
        if source.startswith(module):
            return module
    return source


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def run_cross_checks(spec_paths: list[Path], level_id: str) -> dict:
    specs_by_module = {}
    resolved_paths = []
    for p in spec_paths:
        spec = load_spec(p)
        module = get_module(spec, p)
        specs_by_module[module] = spec
        resolved_paths.append(str(p.relative_to(PROJECT_ROOT)) if p.is_relative_to(PROJECT_ROOT) else str(p))

    modules = sorted(specs_by_module.keys())
    checks_run = []
    v = CrossValidator()

    for desc, fn in CROSS_CHECKS:
        fn(specs_by_module, v)
        checks_run.append(desc)

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "level_id": level_id,
        "spec_paths": resolved_paths,
        "modules": modules,
        "cross_checks_run": checks_run,
        "errors": v.errors,
        "reviews": v.reviews,
        "stats": {"errors": len(v.errors), "reviews": len(v.reviews)},
    }
    return result, v

def collect_specs_by_level(level_id: str) -> list[Path]:
    specs_dir = PROJECT_ROOT / "specs"
    matched = []
    for p in sorted(specs_dir.glob("*.spec.json")):
        spec = load_spec(p)
        lid = get_level_id(spec, p)
        if lid == level_id:
            matched.append(p)
    return matched

def print_result(result: dict, v: CrossValidator):
    modules_str = ",".join(result["modules"])
    n_checks = len(result["cross_checks_run"])
    print(f"modules={modules_str} cross_checks={n_checks}")
    for e in v.errors:
        print(f"  [ERROR] {e['field_path']}  {e['rule']}: {e['msg']}")
    for r in v.reviews:
        print(f"  [REVIEW] {r['field_path']}  {r['rule']}: {r['msg']}")
    print(f"errors={result['stats']['errors']} reviews={result['stats']['reviews']}")


def write_output(result: dict, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    out_display = out_path.relative_to(PROJECT_ROOT) if out_path.is_relative_to(PROJECT_ROOT) else out_path
    print(f"OK: warnings written to {out_display}")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--level-id", metavar="ID", help="按 level_id 扫描 specs/")
    group.add_argument("--specs", nargs="+", metavar="FILE", help="直接列 spec 文件（fallback）")
    parser.add_argument("--output", metavar="FILE", default=None,
                        help=f"输出路径（默认: --level-id 模式 → {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)}；--specs 模式 → /tmp/.cross_warnings_specs.json，避免污染正式告警）")
    args = parser.parse_args()

    if args.output:
        out_path = Path(args.output)
    elif args.level_id:
        out_path = DEFAULT_OUTPUT
    else:
        out_path = Path("/tmp/.cross_warnings_specs.json")

    if args.level_id:
        level_id = args.level_id
        spec_paths = collect_specs_by_level(level_id)
        if len(spec_paths) < 2:
            print(f"OK: only {len(spec_paths)} spec(s) for level_id, no cross-check applied")
            sys.exit(0)
    else:
        spec_paths = [Path(p) for p in args.specs]
        for p in spec_paths:
            if not p.exists():
                print(f"ERROR: file not found: {p}", file=sys.stderr)
                sys.exit(1)
        if len(spec_paths) < 2:
            spec = load_spec(spec_paths[0])
            level_id = get_level_id(spec, spec_paths[0])
            print(f"OK: only {len(spec_paths)} spec(s) for level_id, no cross-check applied")
            sys.exit(0)
        # validate consistent level_id
        level_ids = []
        for p in spec_paths:
            spec = load_spec(p)
            level_ids.append(get_level_id(spec, p))
        if len(set(level_ids)) > 1:
            print(f"ERROR: specs have mismatched level_ids: {list(zip([str(p) for p in spec_paths], level_ids))}", file=sys.stderr)
            sys.exit(1)
        level_id = level_ids[0]

    result, v = run_cross_checks(spec_paths, level_id)
    print_result(result, v)
    write_output(result, out_path)

    sys.exit(1 if v.errors else 0)

if __name__ == "__main__":
    main()
