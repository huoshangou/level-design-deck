#!/usr/bin/env python3
"""从 gameplay/prop HTML 模板中提取字段结构，供 /fill-doc skill 使用。

用法：
  python3 tools/extract_doc_fields.py templates/html/gameplay_template_v1.5.html
  python3 tools/extract_doc_fields.py --all   # 处理 templates/html/ 下所有模板

输出：同目录的 {template_stem}_fields.json

JSON 结构：
{
  "template_kind": "gameplay",
  "template_version": "1.5",
  "sections": [
    {
      "num": "03",
      "id": "overview",
      "name": "设计概述",
      "fields": [
        {"key": "design_goal", "label": "设计目标与体验"},
        ...
      ],
      "checklist_controls": []   # 该 section 是否被 checklist 控制显隐
    },
    ...
  ],
  "checklist_items": [
    {"id": "chk-3c", "label": "3C需求", "controls": "req-3c"}
  ]
}
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path

try:
    from html.parser import HTMLParser
except ImportError:
    raise SystemExit("需要 Python 3.x 标准库 html.parser")


class TemplateParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._stack: list[dict] = []
        self.sections: list[dict] = []
        self.checklist_items: list[dict] = []
        self.template_kind: str = ""
        self.template_version: str = ""
        self._current_section: dict | None = None
        self._in_h2 = False
        self._h2_text = ""
        self._current_field_label = ""

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)

        # 读 meta 标签
        if tag == "meta":
            name = attrs_d.get("name", "")
            content = attrs_d.get("content", "")
            if name == "template-kind":
                self.template_kind = content
            elif name == "template-version":
                self.template_version = content

        # section / sub-section 开始
        if tag == "section":
            sec_id = attrs_d.get("id", "")
            sec = {"id": sec_id, "name": "", "num": "", "fields": [], "checklist_controlled": False}
            self.sections.append(sec)
            self._current_section = sec

        if tag == "div" and "sub-section" in attrs_d.get("class", ""):
            sec_id = attrs_d.get("id", "")
            sec = {"id": sec_id, "name": "", "num": "", "fields": [], "checklist_controlled": True}
            self.sections.append(sec)
            self._current_section = sec

        # h2 标题（section 编号+名称）
        if tag == "h2":
            self._in_h2 = True
            self._h2_text = ""

        # data-field 字段
        field_key = attrs_d.get("data-field", "")
        if field_key and self._current_section is not None:
            # 跳过 header 区域（没有 section 父元素的字段）
            label = attrs_d.get("placeholder", "") or attrs_d.get("title", "") or field_key
            entry = {"key": field_key, "label": label, "tag": tag}
            # select 字段记录 options
            if tag == "select":
                entry["type"] = "select"
            elif tag == "input" and attrs_d.get("type") == "date":
                entry["type"] = "date"
            else:
                entry["type"] = "text"
            if not any(f["key"] == field_key for f in self._current_section["fields"]):
                self._current_section["fields"].append(entry)

        # checklist item
        if tag == "input" and attrs_d.get("type") == "checkbox":
            chk_id = attrs_d.get("id", "")
            controls = attrs_d.get("data-controls", "")
            if chk_id.startswith("chk-") and controls:
                self.checklist_items.append({"id": chk_id, "label": "", "controls": controls})

    def handle_endtag(self, tag):
        if tag == "h2":
            self._in_h2 = False
            if self._current_section and not self._current_section["name"]:
                text = re.sub(r"\s+", " ", self._h2_text).strip()
                # 去掉末尾的 button 文字（"折叠" / "展开"）
                text = re.sub(r"\s*(折叠|展开)\s*$", "", text).strip()
                # 提取编号和名称，如 "03设计概述" 或 "6.1 玩法流程图"
                m = re.match(r"^(\d+(?:\.\d+)?)\s*(.*)", text)
                if m:
                    self._current_section["num"] = m.group(1)
                    self._current_section["name"] = m.group(2).strip()
                else:
                    self._current_section["name"] = text

        if tag == "section":
            self._current_section = None

    def handle_data(self, data):
        if self._in_h2:
            self._h2_text += data


def extract(html_path: Path) -> dict:
    parser = TemplateParser()
    parser.feed(html_path.read_text(encoding="utf-8"))

    # 过滤：只保留有 fields 的 section，并去掉纯元数据 section（id 为空）
    sections = [s for s in parser.sections if s["fields"] or s["name"]]

    return {
        "template_kind": parser.template_kind,
        "template_version": parser.template_version,
        "source": html_path.name,
        "sections": sections,
        "checklist_items": parser.checklist_items,
    }


def main():
    args = sys.argv[1:]
    html_dir = Path(__file__).parent.parent / "templates" / "html"

    if "--all" in args:
        targets = list(html_dir.glob("*.html"))
    else:
        if not args:
            print(__doc__)
            sys.exit(0)
        targets = [Path(a) for a in args if not a.startswith("--")]

    for p in targets:
        result = extract(p)
        out = p.parent / (p.stem + "_fields.json")
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        n_fields = sum(len(s["fields"]) for s in result["sections"])
        print(f"✓ {p.name}  →  {out.name}  ({len(result['sections'])} sections, {n_fields} fields)")


if __name__ == "__main__":
    main()
