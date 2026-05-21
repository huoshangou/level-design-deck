"""已生成设计文档管理 API。

docs/ 目录存放 cc fill-gamedoc 生成的 filled HTML 文档。
不进 git（.gitignore 已排除），由 webapp 本地管理。
"""

from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
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


@router.put("/{filename}")
async def save_doc(filename: str, request: Request, settings=Depends(get_settings)):
    """模板预览栏内编辑后回写。

    安全约束：
    - filename 不允许路径分隔符（防 ../ 逃出 docs/）
    - 仅允许 .html
    - 写入前必须确保 docs/ 目录已存在
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="invalid filename")
    if not filename.endswith(".html"):
        raise HTTPException(status_code=400, detail="only .html allowed")
    docs_dir = settings.project_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    target = docs_dir / filename
    body = await request.body()
    if len(body) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="payload too large (>50MB)")
    target.write_bytes(body)
    stat = target.stat()
    return {"ok": True, "filename": filename, "size_bytes": stat.st_size, "mtime": stat.st_mtime}
