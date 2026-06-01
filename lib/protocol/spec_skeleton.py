#!/usr/bin/env python3
"""
spec_skeleton.py — 同 level_id 多 spec → 统一待填清单

给 cc 接力填 spec 前必读：一次看全关卡所有 module 的字段状态 + 跨 module ref 健康度。

输入：--level-id <id>（自动扫 specs/<module>_<level_id>.spec.json）或 --specs <paths>
输出：JSON（默认）或 --markdown

约束：stdlib only / < 300 行 / fail loud
[来源: Steve 直接指示（2026-05-28）+ 第一原理推导]
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = PROJECT_ROOT / "specs"
SCHEMA_DIR = PROJECT_ROOT / "schema"
PLACEHOLDER_RE = re.compile(r"待定|待补充|TBD|TODO|参考xxx|参考XXX", re.IGNORECASE)
TBD_RE = re.compile(r"^\[?待对接\]?$")

# 与 cross_check.py _ZONE_REF_RULES 对齐：(src_mod, src_coll, src_key, tgt_mod, tgt_field)
CROSS_REF_RULES = [
    ("lighting_req", "ambience_refs", "region_id", "spatial_layout", "layout.shapes[].label"),
    ("vfx_req", "effects", "zone_id", "spatial_layout", "layout.shapes[].label"),
    ("audio_req", "ambient_sounds", "zone_id", "spatial_layout", "layout.shapes[].label"),
    ("atmosphere_ref", "zones", "zone_id", "spatial_layout", "layout.shapes[].label"),
    ("asset_list", "assets", "ref_zone_id", "spatial_layout", "layout.shapes[].label"),
    ("storyboard", "panels", "zone_id", "spatial_layout", "layout.shapes[].label"),
    ("storyboard", "panels", "beat_id", "bubble_diagram", "nodes[].id"),
]
KNOWN_MODULES = ["level_overview", "atmosphere_ref", "bubble_diagram", "spatial_layout",
                 "lighting_req", "vfx_req", "audio_req", "asset_list", "storyboard"]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {path}: {e}")


def discover_specs(level_id: str) -> list:
    """按 level_id 找 specs/<module>_<level_id>.spec.json"""
    if not SPECS_DIR.exists():
        raise FileNotFoundError(f"specs dir not found: {SPECS_DIR}")
    matches = []
    for module in KNOWN_MODULES:
        candidate = SPECS_DIR / f"{module}_{level_id}.spec.json"
        if candidate.exists():
            matches.append((module, candidate))
    if not matches:
        raise FileNotFoundError(f"no specs found for level_id={level_id!r} under {SPECS_DIR}")
    return matches


def infer_module_from_spec_id(spec_id: str) -> str:
    for module in sorted(KNOWN_MODULES, key=len, reverse=True):
        if spec_id.startswith(f"{module}_") or spec_id == f"demo_{module}":
            return module
    return ""


def iter_fields(schema: dict, spec, path: str = "", required_set=None):
    """递归 schema yield (path, field_schema, current_value, is_required)"""
    if required_set is None:
        required_set = set()
    t = schema.get("type")
    if t == "object":
        sub_req = set(schema.get("required", []))
        for key, sub in schema.get("properties", {}).items():
            sub_path = f"{path}.{key}" if path else key
            sub_val = spec.get(key) if isinstance(spec, dict) else None
            yield from iter_fields(sub, sub_val, sub_path, sub_req)
    elif t == "array":
        items = spec if isinstance(spec, list) else []
        if not items:
            yield (path, schema, [], path.split(".")[-1] in required_set)
            return
        for i, item in enumerate(items):
            yield from iter_fields(schema.get("items", {}), item, f"{path}[{i}]", set())
    else:
        leaf_key = path.split(".")[-1].split("[")[0]
        yield (path, schema, spec, leaf_key in required_set)


def classify(value, is_required: bool) -> str:
    if value in (None, "", []):
        return "required_missing" if is_required else "empty"
    if isinstance(value, str):
        if PLACEHOLDER_RE.search(value):
            return "placeholder"
        if TBD_RE.match(value.strip()):
            return "tbd_pending"
    return "filled"


def truncate(s, n=80):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"


def build_module_skeleton(module: str, spec_path: Path, ref_lookup: dict = None) -> dict:
    spec = load_json(spec_path)
    schema_path = SCHEMA_DIR / f"{module}.schema.json"
    schema = load_json(schema_path)
    ref_lookup = ref_lookup or {}
    fields_out = []
    stats = {"total": 0, "filled": 0, "empty": 0, "placeholder": 0,
             "tbd_pending": 0, "required_missing": 0}
    LEAF_TYPES = ("string", "number", "integer", "boolean")
    for path, fs, current, is_required in iter_fields(schema, spec):
        if isinstance(current, (dict, list)) and current and fs.get("type") not in LEAF_TYPES:
            continue
        status = classify(current, is_required)
        stats["total"] += 1
        stats[status] = stats.get(status, 0) + 1
        entry = {"path": path, "label": fs.get("title", path.split(".")[-1]),
                 "type": fs.get("type", "unknown"), "required": is_required, "status": status,
                 "current": truncate(current) if current not in (None, "", []) else None}
        if fs.get("enum"):
            entry["enum"] = fs["enum"]
        if fs.get("description"):
            entry["desc"] = truncate(fs["description"], 120)
        if path in ref_lookup:
            entry["cross_ref"] = ref_lookup[path]
        fields_out.append(entry)
    return {"module": module, "spec_path": str(spec_path.relative_to(PROJECT_ROOT)),
            "schema_path": str(schema_path.relative_to(PROJECT_ROOT)),
            "schema_version": schema.get("version", "unknown"),
            "stats": stats, "fields": fields_out}


def collect_cross_refs(specs_by_module: dict) -> list:
    out = []
    spatial_labels = {(s.get("label") or "").strip() for s in
                      (specs_by_module.get("spatial_layout") or {}).get("layout", {}).get("shapes", [])
                      if isinstance(s, dict)} - {""}
    bubble_ids = {n["id"] for n in (specs_by_module.get("bubble_diagram") or {}).get("nodes", [])
                  if isinstance(n, dict) and n.get("id")}
    pools = {("spatial_layout", "layout.shapes[].label"): spatial_labels,
             ("bubble_diagram", "nodes[].id"): bubble_ids}
    for src_mod, src_coll, src_key, tgt_mod, tgt_field in CROSS_REF_RULES:
        src_spec = specs_by_module.get(src_mod)
        if not src_spec:
            continue
        items = src_spec.get(src_coll, [])
        if not isinstance(items, list):
            continue
        pool = pools.get((tgt_mod, tgt_field), set())
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            val = (item.get(src_key) or "").strip()
            if not val:
                continue
            status = "matched" if val in pool else ("broken" if pool else "target_missing")
            out.append({"from": f"{src_mod}.{src_coll}[{i}].{src_key}", "from_value": val,
                        "to_module": tgt_mod, "to_field": tgt_field, "status": status})
    return out


def build_skeleton(level_id: str, spec_paths: list) -> dict:
    specs_by_module = {m: load_json(p) for m, p in spec_paths}
    cross_refs = collect_cross_refs(specs_by_module)
    # 按 module → {local_path: ref_info} 建 lookup，用于注入到 fields
    by_module_lookup = {}
    for r in cross_refs:
        src_mod, _, local_path = r["from"].partition(".")
        by_module_lookup.setdefault(src_mod, {})[local_path] = {
            "to_module": r["to_module"], "to_field": r["to_field"], "status": r["status"]}
    modules_out = [build_module_skeleton(m, p, by_module_lookup.get(m, {}))
                   for m, p in spec_paths]
    broken = [r for r in cross_refs if r["status"] == "broken"]
    fields_pending = sum(m["stats"].get(k, 0) for m in modules_out
                         for k in ("empty", "required_missing", "placeholder", "tbd_pending"))
    return {"skeleton_version": "0.2.0", "level_id": level_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "modules": modules_out, "cross_refs": cross_refs,
            "summary": {"modules_total": len(KNOWN_MODULES), "modules_present": len(modules_out),
                        "fields_pending": fields_pending, "cross_refs_total": len(cross_refs),
                        "cross_refs_broken": len(broken)}}


def render_markdown(skel: dict) -> str:
    lines = [f"# Spec Skeleton · {skel['level_id']}", ""]
    s = skel["summary"]
    lines.append(f"**进度**：{s['modules_present']}/{s['modules_total']} module · "
                 f"{s['fields_pending']} 字段待填 · cross_ref {s['cross_refs_total']} "
                 f"({s['cross_refs_broken']} broken)")
    lines.append("")
    for m in skel["modules"]:
        ms = m["stats"]
        lines.append(f"## {m['module']} (v{m['schema_version']})")
        lines.append(f"_{m['spec_path']}_ · {ms['filled']}/{ms['total']} filled, "
                     f"{ms.get('empty', 0)} empty, {ms.get('required_missing', 0)} required_missing, "
                     f"{ms.get('placeholder', 0)} placeholder, {ms.get('tbd_pending', 0)} tbd")
        lines.append("")
        for f in m["fields"]:
            ref_mark = ""
            if f.get("cross_ref"):
                r = f["cross_ref"]
                sym = {"matched": "→✓", "broken": "→✗", "target_missing": "→?"}.get(r["status"], "→?")
                ref_mark = f" `{sym}{r['to_module']}`"
            marker = {"filled": "✓", "empty": "·", "required_missing": "❗",
                      "placeholder": "⚠", "tbd_pending": "⏳"}.get(f["status"], "?")
            label = f["label"]
            cur = f["current"] if f["current"] is not None else ""
            lines.append(f"- {marker} `{f['path']}` **{label}** — {cur}{ref_mark}")
        lines.append("")
    if skel["cross_refs"]:
        lines.append("## Cross-module refs")
        for r in skel["cross_refs"]:
            mark = {"matched": "✓", "broken": "✗", "target_missing": "?"}.get(r["status"], "?")
            lines.append(f"- {mark} `{r['from']}` = {r['from_value']!r} → {r['to_module']}.{r['to_field']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--level-id", help="按 level_id 自动找 specs/<module>_<level_id>.spec.json")
    g.add_argument("--specs", nargs="+", type=Path, help="显式列 spec 文件路径")
    parser.add_argument("--markdown", action="store_true", help="输出 markdown 而非 JSON")
    parser.add_argument("--output", type=Path, help="写文件而非 stdout")
    args = parser.parse_args()

    if args.level_id:
        spec_paths = discover_specs(args.level_id)
        level_id = args.level_id
    else:
        spec_paths = []
        for p in args.specs:
            spec = load_json(p)
            spec_id = spec.get("meta", {}).get("spec_id", "")
            module = infer_module_from_spec_id(spec_id)
            if not module:
                sys.exit(f"ERROR: cannot infer module from spec_id={spec_id!r} ({p})")
            spec_paths.append((module, p))
        first_level_ids = {load_json(p).get("meta", {}).get("level_id") for _, p in spec_paths}
        first_level_ids.discard(None)
        if len(first_level_ids) > 1:
            sys.exit(f"ERROR: specs span multiple level_ids: {first_level_ids}")
        level_id = first_level_ids.pop() if first_level_ids else "unknown"

    skel = build_skeleton(level_id, spec_paths)
    out = render_markdown(skel) if args.markdown else json.dumps(skel, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
