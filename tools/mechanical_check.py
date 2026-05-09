#!/usr/bin/env python3
"""
mechanical_check.py

机械检测器：spec 与 schema 对比，输出强档(ERROR) + 中档(REVIEW) 告警。
不引入 jsonschema 依赖（公司防火墙），自己写简化 validator。

强档（ERROR）：required 缺失 / type 不对 / enum 越界 / pattern 不匹配 / minLength 不达标 / additionalProperties 违反
中档（REVIEW）：占位符残留 / AI caveat 话术
弱档（AI confidence）：M1 不做。

使用：
  python3 tools/mechanical_check.py specs/demo_lighting_req.spec.json schema/lighting_req.schema.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / ".warnings.json"

PLACEHOLDER_RE = re.compile(r"待定|待补充|TBD|TODO|参考xxx|参考XXX|^~+$|^\?+$", re.IGNORECASE)
CAVEAT_RE = re.compile(r"（待[一-鿿]*确认）|\(待[一-鿿]*确认\)|暂用[一-鿿]+代替|临时[一-鿿]+方案")


class Validator:
    def __init__(self, schema):
        self.schema = schema
        self.errors = []
        self.reviews = []

    def add_error(self, path, rule, msg):
        self.errors.append({"level": "ERROR", "field_path": path, "rule": rule, "msg": msg})

    def add_review(self, path, rule, msg):
        self.reviews.append({"level": "REVIEW", "field_path": path, "rule": rule, "msg": msg})

    def check(self, instance, schema=None, path=""):
        schema = schema or self.schema
        t = schema.get("type")

        # type check
        if t == "object":
            if not isinstance(instance, dict):
                self.add_error(path, "type", f"expected object, got {type(instance).__name__}")
                return
            self._check_object(instance, schema, path)
        elif t == "array":
            if not isinstance(instance, list):
                self.add_error(path, "type", f"expected array, got {type(instance).__name__}")
                return
            self._check_array(instance, schema, path)
        elif t == "string":
            if not isinstance(instance, str):
                self.add_error(path, "type", f"expected string, got {type(instance).__name__}")
                return
            self._check_string(instance, schema, path)
        elif t == "number":
            if not isinstance(instance, (int, float)) or isinstance(instance, bool):
                self.add_error(path, "type", f"expected number, got {type(instance).__name__}")
                return
        elif t == "integer":
            if not isinstance(instance, int) or isinstance(instance, bool):
                self.add_error(path, "type", f"expected integer, got {type(instance).__name__}")
                return
        elif t == "boolean":
            if not isinstance(instance, bool):
                self.add_error(path, "type", f"expected boolean, got {type(instance).__name__}")
                return

    def _check_object(self, instance, schema, path):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        additional_allowed = schema.get("additionalProperties", True)

        for req_field in required:
            if req_field not in instance:
                self.add_error(self._join(path, req_field), "required", f"required field missing")

        for key, value in instance.items():
            if key in props:
                self.check(value, props[key], self._join(path, key))
            elif not additional_allowed:
                self.add_error(self._join(path, key), "additionalProperties",
                               f"unexpected field, additionalProperties=false")

    def _check_array(self, instance, schema, path):
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(instance):
                self.check(item, item_schema, f"{path}[{i}]")

    def _check_string(self, instance, schema, path):
        # length
        min_len = schema.get("minLength")
        if min_len is not None and len(instance) < min_len:
            self.add_error(path, "minLength",
                           f"length {len(instance)} < minLength {min_len}: {instance!r}")

        # enum
        enum = schema.get("enum")
        if enum is not None and instance not in enum:
            self.add_error(path, "enum", f"value {instance!r} not in enum {enum}")

        # pattern
        pattern = schema.get("pattern")
        if pattern is not None and not re.search(pattern, instance):
            self.add_error(path, "pattern", f"value {instance!r} does not match pattern {pattern!r}")

        # 中档：占位符 / caveat（只对 minLength >= 5 的字段查，避免误伤短 ID）
        if min_len is None or min_len >= 5:
            if PLACEHOLDER_RE.search(instance):
                self.add_review(path, "placeholder_residue",
                                f"detected placeholder pattern in: {instance!r}")
            if CAVEAT_RE.search(instance):
                self.add_review(path, "ai_caveat",
                                f"detected AI caveat phrase in: {instance!r}")

    @staticmethod
    def _join(path, key):
        if not path:
            return key
        return f"{path}.{key}"


# === module 语义层 dispatcher (M3.2) ===
# schema 表达不了"图级语义"（id 唯一、edge 端点存在、入口出口）。
# 通用 schema validator 跑完后，按 module 派发到对应语义检查函数。

SEMANTIC_CHECKS = {}


def register_semantic_check(module):
    def deco(f):
        SEMANTIC_CHECKS[module] = f
        return f
    return deco


def infer_module(spec, schema):
    """从 spec.meta.spec_id 前缀或 schema.$id 推断 module 名。"""
    spec_id = spec.get("meta", {}).get("spec_id", "")
    for module in sorted(SEMANTIC_CHECKS.keys(), key=len, reverse=True):
        if spec_id == f"demo_{module}" or spec_id.startswith(f"demo_{module}_") or spec_id.startswith(f"{module}_"):
            return module
    schema_id = schema.get("$id", "")
    for module in sorted(SEMANTIC_CHECKS.keys(), key=len, reverse=True):
        if f"/{module}.schema.json" in schema_id:
            return module
    return None


@register_semantic_check("bubble_diagram")
def check_bubble_diagram(spec, v):
    nodes = spec.get("nodes", []) if isinstance(spec.get("nodes"), list) else []
    edges = spec.get("edges", []) if isinstance(spec.get("edges"), list) else []

    # 1. node id 全 spec 唯一
    seen = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        if nid is None:
            continue  # schema layer 已报 required
        if nid in seen:
            v.add_error(f"nodes[{i}].id", "unique_id", f"duplicate id {nid!r}")
        seen.add(nid)

    # 2. edge.from / edge.to 必须命中已声明 node id
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            continue
        for end in ("from", "to"):
            ref = e.get(end)
            if ref is not None and ref not in seen:
                v.add_error(f"edges[{i}].{end}", "ref_integrity",
                            f"{ref!r} not in nodes (available: {sorted(seen)})")

    # 3. 入口必须存在；出口缺失 = REVIEW（不阻塞，部分流程可能无明确 exit）
    types = [n.get("type") for n in nodes if isinstance(n, dict)]
    if "entry" not in types:
        v.add_error("nodes", "graph_entry", "no node with type=entry (graph needs at least 1 entry)")
    if "exit" not in types:
        v.add_review("nodes", "graph_exit", "no node with type=exit (warning, not blocking)")

    # 4. 孤立节点（无任何 in/out edge）→ REVIEW
    refed = set()
    for e in edges:
        if not isinstance(e, dict):
            continue
        if e.get("from") in seen:
            refed.add(e["from"])
        if e.get("to") in seen:
            refed.add(e["to"])
    for nid in seen:
        if nid not in refed:
            v.add_review(f"nodes[{nid}]", "isolated", f"node {nid!r} has no in/out edge")

    # 5. M3.5: edges[].requires 引用必须命中 nodes[].id（合取前置语法层校验）
    # 祖先可达性留作 M3.x 候选（HUB+loop 下 DAG 语义模糊）
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            continue
        reqs = e.get("requires") or []
        if not isinstance(reqs, list):
            continue
        for j, ref in enumerate(reqs):
            if ref not in seen:
                v.add_error(f"edges[{i}].requires[{j}]", "ref_integrity",
                            f"requires {ref!r} not in nodes (available: {sorted(seen)})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="spec JSON 路径")
    parser.add_argument("schema", type=Path, help="schema JSON 路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"输出告警 JSON（默认 {DEFAULT_OUTPUT}）")
    parser.add_argument("--quiet", action="store_true", help="不打印告警明细，只打 stats")
    args = parser.parse_args()

    if not args.spec.exists():
        sys.exit(f"ERROR: spec not found: {args.spec}")
    if not args.schema.exists():
        sys.exit(f"ERROR: schema not found: {args.schema}")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))

    v = Validator(schema)
    v.check(spec)

    # M3.2: 跑 module 语义层检查（图级断言等 schema 表达不了的）
    module = infer_module(spec, schema)
    fn = SEMANTIC_CHECKS.get(module) if module else None
    if fn:
        fn(spec, v)

    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "spec_path": str(args.spec),
        "schema_path": str(args.schema),
        "errors": v.errors,
        "reviews": v.reviews,
        "stats": {
            "errors": len(v.errors),
            "reviews": len(v.reviews),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"errors={len(v.errors)} reviews={len(v.reviews)}")
    if not args.quiet:
        for e in v.errors:
            print(f"  [ERROR]  {e['field_path']}  {e['rule']}: {e['msg']}")
        for r in v.reviews:
            print(f"  [REVIEW] {r['field_path']}  {r['rule']}: {r['msg']}")
    print(f"OK: warnings written to {args.output}")
    sys.exit(1 if v.errors else 0)


if __name__ == "__main__":
    main()
