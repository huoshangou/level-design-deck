#!/usr/bin/env python3
"""
doc_skeleton.py — 派生 LDD 产出 HTML 文档骨架供 cc 接力修改前先看

输入：HTML 文档路径
输出：stdout Markdown 骨架，含每字段当前值、待填标记、ai-flag 列表、统计摘要

约束（详见 CLAUDE.md）：
- stdlib only（html.parser + re + json + argparse）
- < 250 行
- fail loud：解析异常明确报错

调用示例：
    python3 tools/doc_skeleton.py docs/【玩法】XXX.html
    python3 tools/doc_skeleton.py docs/XXX.html --fields reference/template_fields.json
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIELDS = PROJECT_ROOT / "reference" / "template_fields.json"

# 视为"未填"的 inner HTML 模式
EMPTY_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^\s*<br\s*/?>\s*$", re.I),
    re.compile(r"^\s*&nbsp;\s*$"),
    re.compile(r"【待填写"),
    re.compile(r"YYYY[-/]MM[-/]DD"),
    re.compile(r"^Gameplay Name", re.I),
    re.compile(r"placeholder", re.I),
]

AI_UNCERTAIN_RE = re.compile(r"ai-uncertain")
AI_MISSING_RE = re.compile(r"ai-missing")


class DocParser(HTMLParser):
    """提取所有 data-field 容器的 innerHTML、checkbox/radio 状态、ai-flag 列表。

    data-field 容器可能嵌套（rich 字段含 p/ul/li），用 tag depth stack 匹配闭标签。
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.values = {}            # field_name -> inner HTML (raw)
        self.checkboxes = {}        # id -> bool checked
        self.radios = {}            # name -> value (last checked)
        self.ai_flags = []          # [(id, kind, preview)]
        self._tag_stack = []        # 当前 tag 嵌套栈
        # 多个 data-field 同时打开（理论上不会嵌套，但保险用 list）
        # 每项：{name, start_depth, buf, tag}
        self._open_fields = []
        # 当前在 ai-flag span 内
        self._in_flag = None        # {id, kind, buf}

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self._tag_stack.append(tag)
        depth = len(self._tag_stack)

        # 累积进所有 open fields
        raw = self.get_starttag_text() or ""
        for f in self._open_fields:
            f["buf"].append(raw)
        if self._in_flag is not None:
            self._in_flag["buf"].append(raw)

        # 检测 data-field 开始
        if "data-field" in d:
            self._open_fields.append({
                "name": d["data-field"],
                "start_depth": depth,
                "buf": [],
                "tag": tag,
            })

        # ai-flag span
        cls = d.get("class", "")
        if "ai-flag" in cls and tag == "span":
            kind = "uncertain" if AI_UNCERTAIN_RE.search(cls) else (
                "missing" if AI_MISSING_RE.search(cls) else "other")
            self._in_flag = {"id": d.get("id", ""), "kind": kind, "buf": []}

        # input checkbox / radio
        if tag == "input":
            t = d.get("type", "")
            checked = "checked" in d
            if t == "checkbox" and "id" in d:
                self.checkboxes[d["id"]] = checked
            elif t == "radio" and "name" in d and checked:
                self.radios[d["name"]] = d.get("value", "")

    def handle_endtag(self, tag):
        depth = len(self._tag_stack)

        # 关闭最近一个匹配深度的 data-field
        for f in list(self._open_fields):
            if f["start_depth"] == depth:
                self.values[f["name"]] = "".join(f["buf"]).strip()
                self._open_fields.remove(f)

        # 关闭 ai-flag span
        if self._in_flag is not None and tag == "span":
            text = "".join(self._in_flag["buf"])
            preview = re.sub(r"<[^>]+>", "", text).strip()[:60]
            self.ai_flags.append((self._in_flag["id"], self._in_flag["kind"], preview))
            self._in_flag = None

        # 累积闭标签到 open fields
        for f in self._open_fields:
            f["buf"].append(f"</{tag}>")
        if self._in_flag is not None:
            self._in_flag["buf"].append(f"</{tag}>")

        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data):
        for f in self._open_fields:
            f["buf"].append(data)
        if self._in_flag is not None:
            self._in_flag["buf"].append(data)


def is_empty(value: str) -> bool:
    """判定字段值是否视为"未填"（空白、模板占位、待填标记）。"""
    if not value:
        return True
    for p in EMPTY_PATTERNS:
        if p.search(value):
            return True
    return False


def summarize_value(value: str, kind: str, max_len: int = 60) -> str:
    """缩略字段值供骨架显示。富文本剥标签；mermaid 显示行数+节点数。"""
    if not value:
        return '""'
    if kind == "mermaid" or "mermaid" in value.lower() and "flowchart" in value.lower():
        lines = [ln for ln in value.split("\n") if ln.strip()]
        # 节点数粗略：含 `[xxx]` 或 `{xxx}` 的行
        node_lines = [ln for ln in lines if re.search(r"[\[\{]", ln)]
        return f"(mermaid, {len(lines)} 行, ~{len(node_lines)} 节点)"
    # 剥标签
    plain = re.sub(r"<[^>]+>", "", value).strip()
    plain = re.sub(r"\s+", " ", plain)
    if len(plain) > max_len:
        return f'"{plain[:max_len]}..."'
    return f'"{plain}"'


def classify_kind(field: dict, value: str) -> str:
    """根据字段名 / 内容粗推类型，用于显示和判定。"""
    name = field.get("name", "")
    if "mermaid" in name or "flowchart" in name and "description" not in name:
        return "mermaid"
    ctrl = field.get("ctrl_type", "")
    if ctrl == "contenteditable":
        return "text"
    if ctrl == "static":
        return "static"
    return ctrl or "unknown"


def render_skeleton(html_path: Path, fields_index: dict) -> str:
    """渲染骨架文本，返回 Markdown 字符串。"""
    html = html_path.read_text(encoding="utf-8")
    parser = DocParser()
    parser.feed(html)

    field_defs = fields_index.get("fields", [])
    section_defs = {s["id"]: s for s in fields_index.get("sections", [])}

    # 按 section 分组
    by_section: dict[str, list] = {}
    for f in field_defs:
        sec = f.get("section", "?")
        by_section.setdefault(sec, []).append(f)

    # 输出
    out = []
    rel = html_path.name
    out.append(f"# 文档骨架 — {rel}")
    out.append(f"模板字段：{len(field_defs)} 项 / sections {len(section_defs)}")
    out.append("")

    stat_filled = 0
    stat_empty = 0
    stat_uncertain = len([f for f in parser.ai_flags if f[1] == "uncertain"])
    stat_missing = len([f for f in parser.ai_flags if f[1] == "missing"])

    # header 段单独显示（fill-gamedoc 3.1.5 头部 meta 必填 checklist 对照）
    header_fields = by_section.get("header", []) + by_section.get("info", [])
    if header_fields:
        out.append("## 头部 meta（13 项必填 checklist 见 fill-gamedoc 3.1.5）")
        for f in header_fields:
            name = f["name"]
            value = parser.values.get(name, "")
            kind = classify_kind(f, value)
            empty = is_empty(value)
            mark = "❗待填" if empty else "✓"
            if empty:
                stat_empty += 1
            else:
                stat_filled += 1
            out.append(f"- `{name}` ({kind}) {summarize_value(value, kind)} {mark}")
        out.append("")

    # 其他 section
    for sec_id, sec_def in section_defs.items():
        if sec_id in ("header", "info"):
            continue
        fs = by_section.get(sec_id, [])
        if not fs:
            continue
        out.append(f"## [{sec_id}] {sec_def['title']}")
        for f in fs:
            name = f["name"]
            value = parser.values.get(name, "")
            kind = classify_kind(f, value)
            empty = is_empty(value)
            mark = "❗待填" if empty else "✓"
            if empty:
                stat_empty += 1
            else:
                stat_filled += 1
            out.append(f"- `{name}` ({kind}) {summarize_value(value, kind)} {mark}")
        out.append("")

    # ai-flag 列表
    if parser.ai_flags:
        out.append("## ai-flag 待清理")
        for fid, kind, preview in parser.ai_flags:
            tag = "⚠ 待确认" if kind == "uncertain" else ("❌ 待填" if kind == "missing" else "?")
            out.append(f"- `{fid}` {tag}: {preview}")
        out.append("")

    # 统计
    out.append("## 合计")
    out.append(
        f"字段 {len(field_defs)} / 已填 {stat_filled} / ❗ 待填 {stat_empty} / "
        f"⚠ ai-uncertain {stat_uncertain} / ❌ ai-missing {stat_missing}")

    # checkbox 状态（简短）
    checked = [k for k, v in parser.checkboxes.items() if v]
    if checked:
        out.append(f"\n## checkbox 已勾选\n- {', '.join(checked[:15])}"
                   + (f" ...({len(checked)} 共)" if len(checked) > 15 else ""))

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1] if __doc__ else "")
    ap.add_argument("html_path", help="HTML 文档路径")
    ap.add_argument("--fields", default=str(DEFAULT_FIELDS),
                    help=f"template_fields.json 路径（默认 {DEFAULT_FIELDS}）")
    args = ap.parse_args()

    html_path = Path(args.html_path).resolve()
    if not html_path.exists():
        print(f"ERROR: 文档不存在 {html_path}", file=sys.stderr)
        sys.exit(1)

    fields_path = Path(args.fields).resolve()
    if not fields_path.exists():
        print(f"ERROR: template_fields.json 不存在 {fields_path}", file=sys.stderr)
        sys.exit(1)

    fields_index = json.loads(fields_path.read_text(encoding="utf-8"))
    skeleton = render_skeleton(html_path, fields_index)
    print(skeleton)


if __name__ == "__main__":
    main()
