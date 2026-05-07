#!/usr/bin/env python3
"""
render.py

把 spec.json 套到 .html.tmpl 模板，输出 HTML。

支持的占位符（M1 简化版）：
- {{path.to.field}}              变量替换（dot path）
- {{#each path}}...{{/each}}     数组循环（each 内部用 {{this}} 取当前项，或 {{field}} 取当前对象的字段）

使用：
  python3 tools/render.py specs/demo_lighting_req.spec.json templates/lighting_req.html.tmpl outputs/demo.html
"""

import argparse
import re
import json
import sys
from pathlib import Path

EACH_RE = re.compile(r"\{\{#each\s+([^\s}]+)\s*\}\}(.*?)\{\{/each\}\}", re.DOTALL)
VAR_RE = re.compile(r"\{\{\s*([^\s}]+?)\s*\}\}")


def get_path(data, path):
    """从 data 按 dot path 取值。失败返回 ''."""
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part, "")
        else:
            return ""
    return cur if cur is not None else ""


def render_vars(text, data):
    """替换所有 {{path}} 变量。"""
    def replace(m):
        path = m.group(1)
        value = get_path(data, path)
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    return VAR_RE.sub(replace, text)


def render_each(template, data):
    """先展开所有 {{#each path}}...{{/each}}，再返回。"""
    def replace(m):
        path = m.group(1)
        body = m.group(2)
        items = get_path(data, path)
        if not isinstance(items, list):
            return ""
        rendered = []
        for item in items:
            # dict item 直接当 ctx；string/number/...item 包成 {"this": item}，模板用 {{this}} 取
            ctx = item if isinstance(item, dict) else {"this": item}
            rendered.append(render_vars(body, ctx))
        return "".join(rendered)
    return EACH_RE.sub(replace, template)


# === module-aware pre-render enrich (M3.2) ===
# 通用模板引擎不动；按 spec_id 前缀派发到 enricher，注入派生字段（如 mermaid_source）。
# 派生字段约定写到 spec["__derived__"] 命名空间，模板可用 {{__derived__.xxx}} 取值。

NODE_SHAPE = {
    "entry":    ("([", "])"),
    "exit":     ("([", "])"),
    "combat":   ("[", "]"),
    "scene":    ("[", "]"),
    "puzzle":   ("{", "}"),
    "choice":   ("{", "}"),
    "dialogue": ("[/", "/]"),
    "cutscene": ("[\\", "\\]"),
}

EDGE_ARROW = {
    "sequential": "-->",
    "branch":     "-->",
    "optional":   "-.->",
    "loop":       "==>",
    "failure":    "-.->",
}


def spec_to_mermaid(spec):
    """spec.nodes/edges → Mermaid flowchart 文本。"""
    lines = ["graph TD"]
    for n in spec.get("nodes", []):
        if not isinstance(n, dict):
            continue
        l, r = NODE_SHAPE.get(n.get("type"), ("[", "]"))
        label = (n.get("label") or n.get("id", "")).replace('"', '\\"')
        lines.append(f'  {n.get("id", "")}{l}"{label}"{r}')
    for e in spec.get("edges", []):
        if not isinstance(e, dict):
            continue
        et = e.get("type", "sequential")
        arrow = EDGE_ARROW.get(et, "-->")
        lbl = (e.get("label") or "").replace('"', '\\"')
        if et == "failure" and lbl:
            edge_part = f'{arrow}|"{lbl} (失败)"|'
        elif et == "failure":
            edge_part = f'{arrow}|"失败"|'
        elif lbl:
            edge_part = f'{arrow}|"{lbl}"|'
        else:
            edge_part = arrow
        lines.append(f'  {e.get("from", "")} {edge_part} {e.get("to", "")}')
    return "\n".join(lines)


def enrich_for_render(spec):
    """按 spec_id 前缀派发到对应 enricher，注入派生字段。其他 module 默认 noop。"""
    spec_id = spec.get("meta", {}).get("spec_id", "")
    if spec_id.startswith("bubble_diagram_"):
        spec.setdefault("__derived__", {})["mermaid_source"] = spec_to_mermaid(spec)
    return spec


def render(template, spec):
    spec = enrich_for_render(spec)
    # 先展开 each（支持 each 内部嵌套变量），再展开顶层变量
    text = render_each(template, spec)
    text = render_vars(text, spec)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    if not args.spec.exists():
        sys.exit(f"ERROR: spec not found: {args.spec}")
    if not args.template.exists():
        sys.exit(f"ERROR: template not found: {args.template}")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    template = args.template.read_text(encoding="utf-8")

    html = render(template, spec)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")

    print(f"OK: rendered to {args.output} ({len(html)} chars)")


if __name__ == "__main__":
    main()
