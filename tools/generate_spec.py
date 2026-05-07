#!/usr/bin/env python3
"""
generate_spec.py

把 schema + work_docs 字段定义 + demo few-shot + 用户 intent 打包成
self-contained prompt 输出到 stdout。本工具不调 LLM、不连网。
AI 在对话窗口里看 prompt 后产 spec.json，由用户/AI 用 Write 工具落到 specs/。

使用：
  python3 tools/generate_spec.py --module lighting_req --intent "POI: 夜间仓库, 紧张潜行"
  python3 tools/generate_spec.py --module lighting_req --intent "..." --out /tmp/p.md
  python3 tools/generate_spec.py --list-modules
"""

import argparse
import json
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 模块注册表。新增 module 加一行即可。
MODULES = {
    "lighting_req": {
        "schema_path": "schema/lighting_req.schema.json",
        "demo_path": "specs/demo_lighting_req.spec.json",
        "workdoc_key": "poi_lighting_fields",
        "spec_id_pattern": "lighting_req_<poi_short_name>",
    },
    # M3.2: 图状 module，无 work_docs 字段映射（schema 即真源）
    "bubble_diagram": {
        "schema_path": "schema/bubble_diagram.schema.json",
        "demo_path": "specs/demo_bubble_diagram.spec.json",
        "workdoc_key": None,
        "spec_id_pattern": "bubble_diagram_<level_short_name>",
    },
}

WORK_DOCS_PATH = "reference/work_docs_extract.json"

# 与 tools/mechanical_check.py 同步维护（不 import 避免耦合）
PLACEHOLDER_PATTERNS = "待定 / 待补充 / TBD / TODO / 参考xxx / 全 ~~~ / 全 ???"
CAVEAT_PATTERNS = "（待xxx确认） / 暂用xxx代替 / 临时xxx方案"


def load_module(name):
    if name not in MODULES:
        sys.exit(f"ERROR: unknown module '{name}'. Available: {list(MODULES)}")
    cfg = MODULES[name]
    schema = json.loads((PROJECT_ROOT / cfg["schema_path"]).read_text(encoding="utf-8"))
    demo = json.loads((PROJECT_ROOT / cfg["demo_path"]).read_text(encoding="utf-8"))
    # workdoc_key=None 表示图状/无字段映射型 module，schema 即真源
    if cfg["workdoc_key"] is None:
        return cfg, schema, demo, []
    work_docs = json.loads((PROJECT_ROOT / WORK_DOCS_PATH).read_text(encoding="utf-8"))
    fields = work_docs.get(cfg["workdoc_key"], [])
    if not fields:
        sys.exit(f"ERROR: work_docs key '{cfg['workdoc_key']}' empty or missing")
    return cfg, schema, demo, fields


def section_role(module_name):
    return textwrap.dedent(f"""\
        # 任务

        你是 `level-design-deck` 项目的 spec 生成器。
        目标：根据用户的自由文本 intent，产出一份**符合 `{module_name}` schema 的 spec JSON**。

        产出后，你（或 Steve）应该用 Write 工具落到：
            specs/<spec_id>.spec.json
        然后跑：
            python3 tools/mechanical_check.py specs/<spec_id>.spec.json schema/{module_name}.schema.json
            python3 tools/template_diff.py     specs/<spec_id>.spec.json
        两个工具都应输出 0 ERROR / 0 MISSING。""")


def section_anti_pollution():
    return textwrap.dedent("""\
        # 反污染（硬约束）

        本项目独立于 `~/Desktop/level-skill-pipeline/`。生成 spec 时**禁止**：
        - 引用 pipeline 路径 / 旧 module 名（vfx_req / audio_req / spatial_layout 等）
        - 套用 manifest / scorer / HITL 三段术语
        - 复用 pipeline 视觉规范（奶油色出版风等）
        - 凭空臆造 schema 没声明的字段（schema additionalProperties=false 会被机械检测拦下）

        如果你需要为某个判断做注释，使用项目允许的来源标签：
            [来源: schema] / [来源: work_docs] / [来源: Steve 直接指示] / [来源: 第一原理推导]""")


def section_schema(schema):
    return "# Schema（spec 必须严格符合）\n\n```json\n" + json.dumps(schema, ensure_ascii=False, indent=2) + "\n```"


def section_workdoc_fields(fields):
    if not fields:
        return textwrap.dedent("""\
            # Work_docs 字段定义

            该 module 是图状/无字段填空型，**schema 即真源**，无 work_docs 字段映射。
            生成 spec 时严格按 schema.properties 的字段名 + 类型 + enum + 描述办事。""")
    lines = ["# Work_docs 字段定义（业务术语真源）", ""]
    for f in fields:
        req = "required" if f.get("required") else "optional"
        lines.append(f"## {f['name']}  · _{req}_")
        lines.append(f"- **section**: {f.get('section', '')}")
        lines.append(f"- **type**: {f.get('type', '')}")
        lines.append(f"- **description**: {f.get('description', '')}")
        if f.get("source_quote"):
            lines.append(f"- **source_quote**: {f['source_quote']}")
        lines.append("")
    return "\n".join(lines)


def section_demo(demo):
    return "# Few-shot 示例（demo spec，结构合法、风格参考）\n\n```json\n" + json.dumps(demo, ensure_ascii=False, indent=2) + "\n```"


def section_check_rules():
    return textwrap.dedent(f"""\
        # 机械检测规避清单（spec 落盘后会被自动跑）

        **强档 ERROR**（必须全部规避，否则 mechanical_check.py exit 1）：
        - required 字段缺失
        - type 与 schema 声明不符
        - enum 值越界
        - pattern 不匹配（如 spec_id / version 的正则）
        - minLength 不达标（描述类字段普遍要求 ≥10）
        - additionalProperties=false 处多塞字段

        **中档 REVIEW**（应避免，否则告警但不阻塞）：
        - 占位符残留：{PLACEHOLDER_PATTERNS}
        - AI caveat 话术：{CAVEAT_PATTERNS}

        换句话说：**不要在描述里写"待补充"、"暂用 X 代替"**。如果你真的没把握，
        宁可写"基于 intent 推断的 X 风格氛围（公司命名待对接）"这种**有信息的占位**，
        也不要 TBD。""")


def section_intent_and_contract(module_name, cfg, intent):
    return textwrap.dedent(f"""\
        # 用户 intent

        > {intent}

        # 输出契约

        - **spec_id 命名**：`{cfg['spec_id_pattern']}`，poi_short_name 从 intent 推断（小写 + 下划线）
        - **poi_id 命名**：按 intent 推断同样的 short_name，并在描述里注明"公司命名待对接"
        - **version**：起步用 `0.1.0`
        - **owner**：默认 `level`（POI 灯光归关卡组，来自 PDF 第六节）
        - **输出格式**：单个 JSON code block，**不要附加** "我已生成"、"如有问题请告知" 之类话术
        - **落地路径**：`specs/<spec_id>.spec.json`（用 Write 工具）

        生成完后请提示 Steve 跑机械检测和 template diff 验证。""")


def build_prompt(module_name, intent):
    cfg, schema, demo, fields = load_module(module_name)
    parts = [
        section_role(module_name),
        section_anti_pollution(),
        section_schema(schema),
        section_workdoc_fields(fields),
        section_demo(demo),
        section_check_rules(),
        section_intent_and_contract(module_name, cfg, intent),
    ]
    return "\n\n---\n\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--module", help="module 名（见 --list-modules）")
    parser.add_argument("--intent", help="自由文本设计 intent")
    parser.add_argument("--out", type=Path, help="prompt 写到文件而不是 stdout")
    parser.add_argument("--list-modules", action="store_true", help="列出已注册 module 后退出")
    args = parser.parse_args()

    if args.list_modules:
        for name, cfg in MODULES.items():
            print(f"{name}\tschema={cfg['schema_path']}\tdemo={cfg['demo_path']}")
        return

    if not args.module or not args.intent:
        parser.error("--module 和 --intent 都必须提供（或用 --list-modules）")

    prompt = build_prompt(args.module, args.intent)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(prompt, encoding="utf-8")
        print(f"OK: prompt written to {args.out} ({len(prompt)} chars)", file=sys.stderr)
    else:
        sys.stdout.write(prompt)


if __name__ == "__main__":
    main()
