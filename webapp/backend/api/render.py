"""Render endpoint：单 spec / level 完整文档 / deck 视图 / 导出下载。"""

from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import PROJECT_ROOT
from backend.deps import get_store
from backend.services.deck_service import render_deck
from backend.services.render_service import render_level, render_spec
from backend.store.base import SpecNotFound, SpecStore

router = APIRouter(prefix="/api", tags=["render"])


class RenderSpecRequest(BaseModel):
    spec_id: str
    namespace: str = "default"


class RenderLevelRequest(BaseModel):
    level_id: str
    render_missing: bool = True


class RenderDeckRequest(BaseModel):
    level_id: str


@router.post("/render")
def render_spec_endpoint(
    body: RenderSpecRequest,
    store: SpecStore = Depends(get_store),
) -> dict[str, Any]:
    try:
        rec = store.get(body.spec_id, body.namespace)
    except SpecNotFound:
        raise HTTPException(404, f"spec not found: {body.spec_id}")
    return render_spec(rec)


@router.post("/render-level")
def render_level_endpoint(body: RenderLevelRequest) -> dict[str, Any]:
    try:
        return render_level(body.level_id, render_missing=body.render_missing)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/render-deck")
def render_deck_endpoint(body: RenderDeckRequest) -> dict[str, Any]:
    try:
        return render_deck(body.level_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/export")
def export_spec_endpoint(
    body: RenderSpecRequest,
    store: SpecStore = Depends(get_store),
) -> FileResponse:
    try:
        rec = store.get(body.spec_id, body.namespace)
    except SpecNotFound:
        raise HTTPException(404, f"spec not found: {body.spec_id}")
    result = render_spec(rec)
    out_path = PROJECT_ROOT / result["output_path"]
    return FileResponse(
        path=str(out_path),
        media_type="text/html",
        filename=f"{body.spec_id}.html",
        headers={"Content-Disposition": f'attachment; filename="{body.spec_id}.html"'},
    )
