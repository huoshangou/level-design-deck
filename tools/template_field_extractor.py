#!/usr/bin/env python3
"""
template_field_extractor.py

把 gameplay_template.html 提取成纯字段清单 JSON，供 spec diff 使用。
跑一次产出 reference/template_fields.json 后，AI 不再读 template 原文件。

约束（详见 PROJECT.md / CLAUDE.md）：
- 标准库 html.parser，无外部依赖
- 单文件 < 300 行
- 纯结构性提取，不解读字段业务含义
- fail loud：解析异常时明确报错
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "reference" / "templates_snapshot" / "gameplay_template.html"
DEFAULT_OUTPUT = PROJECT_ROOT / "reference" / "template_fields.json"


class TemplateExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        # 章节栈：[(section_id, h2_title)]，最近的是当前所在 section
        self.section_stack = []
        # 收集结果
        self.sections = []          # 顺序保留的 section 列表
        self.sections_seen = set()  # 去重
        self.fields = []
        self.radio_groups = {}      # name -> [{value, default}]
        self.checkboxes = []
        self.tables = []            # {id, section, headers}

        # 状态：当前在收集什么文本
        self._capture_h2_for = None  # section_id 等待 h2 文本
        self._h2_buffer = []
        self._h2_skip_depth = 0      # h2 内遇到 button/span.sec-num 等子标签时暂停吞文本
        # 当前 thead 状态
        self._in_thead = False
        self._th_buffer = None  # list[str]，当前 thead 收集的 th 文本
        self._current_th = None  # 当前 th 文本累积
        self._pending_table_id = None  # tbody id 等待 thead 列头
        # tbody 暂存（同一个 table 可能 thead 在前 tbody 在后）
        self._open_table_thead_headers = None  # 当前 <table> 内已收集的 thead headers
        self._table_depth = 0
        # checkbox label 关联
        self._pending_checkbox = None  # {id, default, controls}
        self._in_label_for_checkbox = False
        self._label_buffer = []

    # ----- helpers -----
    def _current_section(self):
        return self.section_stack[-1][0] if self.section_stack else "header"

    def _attrs_dict(self, attrs):
        return {k: (v if v is not None else "") for k, v in attrs}

    @staticmethod
    def _classes(d):
        return set((d.get("class") or "").split())

    @staticmethod
    def _ctrl_type(tag, d):
        cls = TemplateExtractor._classes(d)
        if "rich-editor-content" in cls:
            return "rich_editor"
        if "mermaid" in cls:
            return "mermaid"
        if tag == "input" and d.get("type", "").lower() == "date":
            return "date_input"
        # 其余 contenteditable 类元素（td/span/h1/div）
        if d.get("contenteditable", "").lower() == "true":
            return "contenteditable"
        # 没标 contenteditable 但有 data-field（少见，保底）
        return "static"

    # ----- parser hooks -----
    def handle_starttag(self, tag, attrs):
        d = self._attrs_dict(attrs)

        if tag == "section" and d.get("id"):
            sec_id = d["id"]
            self.section_stack.append((sec_id, ""))
            if sec_id not in self.sections_seen:
                self.sections.append({"id": sec_id, "title": ""})
                self.sections_seen.add(sec_id)
            self._capture_h2_for = sec_id
            self._h2_buffer = []

        elif tag == "h2" and self._capture_h2_for:
            self._h2_buffer = []  # reset
            self._h2_skip_depth = 0

        # h2 内遇到 button / span.sec-num 等装饰性子标签时停止吞文本
        elif self._capture_h2_for and tag in ("button", "span"):
            cls = self._classes(d)
            if tag == "button" or "sec-num" in cls or "collapse-btn" in cls:
                self._h2_skip_depth += 1

        elif tag == "table":
            self._table_depth += 1
            self._open_table_thead_headers = None

        elif tag == "thead" and self._table_depth > 0:
            self._in_thead = True
            self._th_buffer = []

        elif tag == "th" and self._in_thead:
            self._current_th = []

        elif tag == "tbody" and d.get("id"):
            tid = d["id"]
            self.tables.append({
                "id": tid,
                "section": self._current_section(),
                "headers": list(self._open_table_thead_headers or [])
            })

        elif tag == "input":
            itype = d.get("type", "").lower()
            if itype == "radio":
                name = d.get("name")
                if name:
                    entry = {"value": d.get("value", ""), "default": "checked" in d}
                    self.radio_groups.setdefault(name, []).append(entry)
            elif itype == "checkbox":
                cid = d.get("id")
                if cid:
                    self._pending_checkbox = {
                        "id": cid,
                        "default": "checked" in d,
                        "controls": d.get("data-controls", "")
                    }

        elif tag == "label":
            if self._pending_checkbox and d.get("for") == self._pending_checkbox["id"]:
                self._in_label_for_checkbox = True
                self._label_buffer = []

        # data-field 字段（任意 tag）
        if "data-field" in d:
            self.fields.append({
                "name": d["data-field"],
                "section": self._current_section(),
                "ctrl_type": self._ctrl_type(tag, d)
            })

    def handle_endtag(self, tag):
        if tag == "section" and self.section_stack:
            self.section_stack.pop()
            self._capture_h2_for = None

        elif tag in ("button", "span") and self._capture_h2_for and self._h2_skip_depth > 0:
            self._h2_skip_depth -= 1

        elif tag == "h2" and self._capture_h2_for:
            title = "".join(self._h2_buffer).strip()
            # 写回最近一个匹配的 section
            for sec in reversed(self.sections):
                if sec["id"] == self._capture_h2_for and not sec["title"]:
                    sec["title"] = title
                    break
            self._capture_h2_for = None
            self._h2_buffer = []

        elif tag == "th" and self._in_thead and self._current_th is not None:
            self._th_buffer.append("".join(self._current_th).strip())
            self._current_th = None

        elif tag == "thead" and self._in_thead:
            self._in_thead = False
            self._open_table_thead_headers = list(self._th_buffer or [])
            # 同一 table 后面的 tbody 取这份 headers
            self._th_buffer = []
            # 已写入 self.tables 的 tbody（出现在 thead 之前的少见情况）补 headers
            for t in self.tables:
                if t["headers"] == [] and self._table_depth > 0:
                    t["headers"] = list(self._open_table_thead_headers)

        elif tag == "table":
            self._table_depth = max(0, self._table_depth - 1)
            if self._table_depth == 0:
                self._open_table_thead_headers = None

        elif tag == "label" and self._in_label_for_checkbox:
            label_text = "".join(self._label_buffer).strip()
            if self._pending_checkbox:
                self.checkboxes.append({
                    "id": self._pending_checkbox["id"],
                    "label": label_text,
                    "default": self._pending_checkbox["default"],
                    "controls": self._pending_checkbox["controls"]
                })
                self._pending_checkbox = None
            self._in_label_for_checkbox = False
            self._label_buffer = []

    def handle_data(self, data):
        if self._capture_h2_for and self._h2_buffer is not None and self._h2_skip_depth == 0:
            self._h2_buffer.append(data)
        if self._in_thead and self._current_th is not None:
            self._current_th.append(data)
        if self._in_label_for_checkbox:
            self._label_buffer.append(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"输入 HTML 路径（默认 {DEFAULT_INPUT}）")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"输出 JSON 路径（默认 {DEFAULT_OUTPUT}）")
    args = parser.parse_args()

    if not args.input.exists():
        sys.exit(f"ERROR: input file not found: {args.input}")

    html = args.input.read_text(encoding="utf-8")

    ex = TemplateExtractor()
    try:
        ex.feed(html)
    except Exception as e:
        sys.exit(f"ERROR: HTML parse failed: {e}")

    # 未配对的 checkbox label 容错（极少数 label 顺序异常时忽略）
    if ex._pending_checkbox is not None:
        print(f"WARN: checkbox {ex._pending_checkbox['id']} 的 label 未捕获", file=sys.stderr)

    payload = {
        "source": args.input.name,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "extractor_version": "0.1",
        "stats": {
            "total_fields": len(ex.fields),
            "radio_groups": len(ex.radio_groups),
            "checkboxes": len(ex.checkboxes),
            "named_tables": len(ex.tables),
            "sections": len(ex.sections),
        },
        "sections": ex.sections,
        "fields": ex.fields,
        "radio_groups": ex.radio_groups,
        "checkboxes": ex.checkboxes,
        "tables": ex.tables,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    s = payload["stats"]
    print(f"OK: extracted to {args.output}")
    print(f"  sections={s['sections']} fields={s['total_fields']} "
          f"radio_groups={s['radio_groups']} checkboxes={s['checkboxes']} "
          f"named_tables={s['named_tables']}")


if __name__ == "__main__":
    main()
