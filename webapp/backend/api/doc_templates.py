"""文档模板管理 API。

提供 gameplay / prop 等富文本 HTML 模板的列表和元数据读取。
模板文件放在 PROJECT_ROOT/templates/html/*.html，
通过 /api/doc-templates 列出，通过 /templates/html/ 静态路由直接打开。
"""

from __future__ import annotations
import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import get_settings

router = APIRouter(prefix="/api/doc-templates", tags=["doc-templates"])


class DocTemplateInfo(BaseModel):
    filename: str          # gameplay_template_v1.5.html
    kind: str              # gameplay | prop | unknown
    version: str           # 1.5
    url: str               # /templates/html/gameplay_template_v1.5.html
    has_fields_json: bool  # _fields.json 是否已生成


def _read_meta(html_path: Path) -> tuple[str, str]:
    """快速从 HTML 前 80 行读 meta name="template-kind/version"，不完整解析整个文件。"""
    kind = version = ""
    try:
        lines = []
        with html_path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 80:
                    break
                lines.append(line)
        head = "".join(lines)
        m_kind = re.search(r'meta\s[^>]*name=["\']template-kind["\']\s[^>]*content=["\'](.*?)["\']', head)
        m_ver = re.search(r'meta\s[^>]*name=["\']template-version["\']\s[^>]*content=["\'](.*?)["\']', head)
        if m_kind:
            kind = m_kind.group(1)
        if m_ver:
            version = m_ver.group(1)
    except OSError:
        pass
    return kind, version


@router.get("", response_model=list[DocTemplateInfo])
def list_doc_templates(settings=Depends(get_settings)):
    html_dir = settings.project_root / "templates" / "html"
    if not html_dir.exists():
        return []

    results = []
    for p in sorted(html_dir.glob("*.html")):
        kind, version = _read_meta(p)
        fields_json = p.parent / (p.stem + "_fields.json")
        results.append(DocTemplateInfo(
            filename=p.name,
            kind=kind or "unknown",
            version=version or "",
            url=f"/templates/html/{p.name}",
            has_fields_json=fields_json.exists(),
        ))
    return results


@router.get("/{filename}/fields")
def get_template_fields(filename: str, settings=Depends(get_settings)):
    """返回对应模板的 _fields.json（需先运行 extract_doc_fields.py）。"""
    if not filename.endswith(".html"):
        raise HTTPException(400, "filename 必须以 .html 结尾")
    stem = filename[:-5]
    fields_path = settings.project_root / "templates" / "html" / (stem + "_fields.json")
    if not fields_path.exists():
        raise HTTPException(404, f"{stem}_fields.json 不存在，请先运行 tools/extract_doc_fields.py")
    return json.loads(fields_path.read_text(encoding="utf-8"))
