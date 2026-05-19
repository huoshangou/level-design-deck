"""已生成设计文档管理 API。

docs/ 目录存放 cc fill-gamedoc 生成的 filled HTML 文档。
不进 git（.gitignore 已排除），由 webapp 本地管理。
"""

from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.deps import get_settings

router = APIRouter(prefix="/api/docs", tags=["docs"])


class DocInfo(BaseModel):
    filename: str      # gameplay_居酒屋夜战.html
    url: str           # /docs/gameplay_居酒屋夜战.html
    kind: str          # gameplay | prop | unknown（从文件名推断）
    size_bytes: int
    mtime: float


def _infer_kind(filename: str) -> str:
    name = filename.lower()
    if name.startswith("gameplay") or "【玩法】" in filename:
        return "gameplay"
    if name.startswith("prop") or name.startswith("【"):
        return "prop"
    return "unknown"


@router.get("", response_model=list[DocInfo])
def list_docs(settings=Depends(get_settings)):
    docs_dir = settings.project_root / "docs"
    if not docs_dir.exists():
        return []
    results = []
    for p in sorted(docs_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = p.stat()
        results.append(DocInfo(
            filename=p.name,
            url=f"/docs/{p.name}",
            kind=_infer_kind(p.name),
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
        ))
    return results
