#!/usr/bin/env python3
"""
regenerate_field.py

把 spec 现有内容 + 目标字段当前值 + 该字段 sub-schema + 用户 hint
打包成 self-contained prompt 输出到 stdout。本工具不调 LLM、不连网。
AI 在对话窗口里看 prompt 后给新值，由用户/AI 用 Edit 工具原位覆写。

使用：
  python3 tools/regenerate_field.py specs/demo_lighting_req.spec.json map_constraint.description
  python3 tools/regenerate_field.py specs/demo_lighting_req.spec.json mission_constraint.description --hint "改成晨雾"
  python3 tools/regenerate_field.py specs/demo_lighting_req.spec.json bogus.path  # exit 1 + 列出有效 keys
"""

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 与 tools/mechanical_check.py 同步维护
PLACEHOLDER_PATTERNS = "待定 / 待补充 / TBD / TODO / 参考xxx / 全 ~~~ / 全 ???"
CAVEAT_PATTERNS = "（待xxx确认） / 暂用xxx代替 / 临时xxx方案"

# 模块注册表（与 tools/generate_spec.py 同步）
MODULES = {
    "lighting_req": {"lvm_generated": True},
    "bubble_diagram": {"lvm_generated": True},
    "spatial_layout": {"lvm_generated": False},
    "level_overview": {"lvm_generated": True},
}


def infer_schema_path(spec_path):
    """从 spec 文件名匹配 schema/<module>.schema.json。
    扫 schema/ 目录，找最长 module 名是 spec stem 子串的那个。
    例：demo_lighting_req.spec.json / lighting_req_warehouse.spec.json 都匹配 lighting_req。"""
    schema_dir = PROJECT_ROOT / "schema"
    name = spec_path.stem.replace(".spec", "")
    candidates = sorted(
        (p.name[:-len(".schema.json")] for p in schema_dir.glob("*.schema.json")),
        key=len, reverse=True,
    )
    for module in candidates:
        if module in name:
            return schema_dir / f"{module}.schema.json", module
    sys.exit(f"ERROR: cannot infer schema for spec '{spec_path.name}'. Tried modules: {list(candidates)}. 用 --schema 显式指定")


SEG_RE = re.compile(r"^([^\[]+)(?:\[([^\]]+)\])?$")


def parse_path(path):
    """'nodes[entry].label' → [('key','nodes'), ('idx','entry'), ('key','label')]
       'nodes[0].label'      → [('key','nodes'), ('idx','0'),     ('key','label')]
       'meta.spec_id'        → [('key','meta'),  ('key','spec_id')]"""
    out = []
    for raw in path.split("."):
        m = SEG_RE.match(raw)
        if not m:
            sys.exit(f"ERROR: malformed path segment {raw!r} in {path!r}")
        out.append(("key", m.group(1)))
        if m.group(2) is not None:
            out.append(("idx", m.group(2)))
    return out


def walk_value(spec, path):
    """按 dot path 在 spec 里取值。支持 array 索引：
       - by-index: nodes[0]
       - by-id:    nodes[entry]（按 item.id 字段匹配）
    返回 (value, exists)。"""
    cur = spec
    for kind, val in parse_path(path):
        if kind == "key":
            if isinstance(cur, dict) and val in cur:
                cur = cur[val]
            else:
                return None, False
        else:  # idx
            if not isinstance(cur, list):
                return None, False
            try:
                cur = cur[int(val)]  # by-index
            except ValueError:
                hit = next((x for x in cur if isinstance(x, dict) and x.get("id") == val), None)
                if hit is None:
                    return None, False
                cur = hit
            except IndexError:
                return None, False
    return cur, True


def walk_schema(schema, path):
    """按 dot path 在 schema 里取 sub-schema。array 索引段会下到 items.schema。
    返回 (sub_schema, error_msg)；error_msg 不为 None 表示路径无效，附该层有效 keys。"""
    cur = schema
    walked = []
    for kind, val in parse_path(path):
        if kind == "key":
            if cur.get("type") != "object":
                return None, f"path 走到 {val!r} 时该层非 object（type={cur.get('type')}），无法继续按 key 下钻"
            props = cur.get("properties", {})
            if val not in props:
                valid = list(props.keys())
                return None, f"path '{path}' 在 '{'.'.join(walked) or '<root>'}' 层找不到 key '{val}'。该层有效 keys: {valid}"
            cur = props[val]
            walked.append(val)
        else:  # idx
            if cur.get("type") != "array":
                return None, f"path 走到 array 索引 [{val}] 时该层不是 array（type={cur.get('type')}）"
            cur = cur.get("items", {})
            walked.append(f"[{val}]")
    return cur, None


def section_role(spec_path, field_path):
    return textwrap.dedent(f"""\
        # 任务

        你是 `level-design-deck` 项目的 spec 单字段重生成器。
        目标：**只**给 `{spec_path.name}` 的 `{field_path}` 字段产出新值。
        - **不要**改其他任何字段
        - **不要**输出整份 spec
        - **只**输出该字段的新值（按 sub-schema 决定的 JSON 类型）""")


def section_anti_pollution():
    return textwrap.dedent("""\
        # 反污染（硬约束）

        - 不引用 pipeline 路径 / 旧 module 名 / manifest scorer HITL 术语
        - 不引入 schema 没声明的子字段
        - 不写 caveat 话术（详见下方机械检测规避）""")


def section_check_rules():
    return textwrap.dedent(f"""\
        # 机械检测规避（写完会被自动跑）

        强档 ERROR：required 缺、type 错、enum 越界、pattern 不匹配、minLength 不达标、additionalProperties 多塞
        中档 REVIEW：
        - 占位符：{PLACEHOLDER_PATTERNS}
        - caveat 话术：{CAVEAT_PATTERNS}""")


def section_current_spec(spec):
    return "# 现有 spec 全文（参考上下文）\n\n```json\n" + json.dumps(spec, ensure_ascii=False, indent=2) + "\n```"


def section_target(field_path, current_value, sub_schema):
    return textwrap.dedent(f"""\
        # 目标字段

        **路径**：`{field_path}`

        **当前值**：
        ```json
        {json.dumps(current_value, ensure_ascii=False, indent=2)}
        ```

        **该字段的 sub-schema**：
        ```json
        {json.dumps(sub_schema, ensure_ascii=False, indent=2)}
        ```""")


def section_hint(hint):
    if not hint:
        return "# 修改 hint\n\n_（用户未提供 hint，请基于 sub-schema 描述和现有 spec 上下文自由发挥，但保持与其他字段语义一致）_"
    return f"# 修改 hint\n\n> {hint}"


def section_contract(spec_path, field_path):
    return textwrap.dedent(f"""\
        # 输出契约 + 落地动作

        1. 输出**单个 JSON code block**，内容 = 该字段的新值（不是整 spec、不是 patch、不是 diff）
        2. 用 Edit 工具替换 `{spec_path}` 中 `{field_path}` 的旧值为新值
           - 用 old_string / new_string 精确匹配，避免误伤其他字段
        3. 跑 `git diff {spec_path}` 验证：**只动了 {field_path} 那部分**，多动一行 = 失败
        4. 跑 `python3 tools/mechanical_check.py {spec_path} schema/<module>.schema.json` 应仍 0 ERROR""")


def build_prompt(spec_path, schema_path, field_path, hint):
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sub_schema, err = walk_schema(schema, field_path)
    if err:
        sys.exit(f"ERROR: {err}")

    current_value, exists = walk_value(spec, field_path)
    if not exists:
        # 字段在 schema 里有定义但 spec 里没填（optional 字段）。允许，标注一下。
        current_value = "<spec 中未提供（optional 字段）>"

    parts = [
        section_role(spec_path, field_path),
        section_anti_pollution(),
        section_check_rules(),
        section_current_spec(spec),
        section_target(field_path, current_value, sub_schema),
        section_hint(hint),
        section_contract(spec_path, field_path),
    ]
    return "\n\n---\n\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path, help="spec JSON 路径")
    parser.add_argument("field_path", help="目标字段 dot path，如 map_constraint.description")
    parser.add_argument("--hint", default="", help="修改方向提示")
    parser.add_argument("--schema", type=Path, help="覆盖 schema 路径（默认从 spec 文件名推断）")
    parser.add_argument("--out", type=Path, help="prompt 写到文件而不是 stdout")
    args = parser.parse_args()

    if not args.spec.exists():
        sys.exit(f"ERROR: spec not found: {args.spec}")

    if args.schema:
        schema_path = args.schema
        if not schema_path.exists():
            sys.exit(f"ERROR: schema not found: {schema_path}")
        # 推断 module 名用于检查
        module = schema_path.stem.replace(".schema", "")
    else:
        schema_path, module = infer_schema_path(args.spec)

    # M3.7: spatial_layout 不支持 LLM 重生成（数据源是 LevelCraft 工具）
    if not MODULES.get(module, {}).get("lvm_generated", True):
        sys.exit(f"ERROR: {module} 数据来源是 LevelCraft 2D 工具，不支持字段重生成。"
                 f"请用 LevelCraft 编辑后导出 JSON，手动更新。")

    prompt = build_prompt(args.spec, schema_path, args.field_path, args.hint)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(prompt, encoding="utf-8")
        print(f"OK: prompt written to {args.out} ({len(prompt)} chars)", file=sys.stderr)
    else:
        sys.stdout.write(prompt)


if __name__ == "__main__":
    main()
