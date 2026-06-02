"""Storyboard 专用端点：prompt 批量拼接 + 图片上传。"""

from __future__ import annotations
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.deps import get_settings, get_store
from backend.store.base import SpecNotFound, SpecStore

router = APIRouter(prefix="/api/storyboard", tags=["storyboard"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


class PromptItem(BaseModel):
    panel_id: str
    title: str
    prompt: str
    negative_prompt: str


class ComposeRequest(BaseModel):
    spec_id: str


class ComposeResponse(BaseModel):
    panels: list[PromptItem]


class UploadResponse(BaseModel):
    relative_path: str
    panel_id: str


class BeatNode(BaseModel):
    id: str
    type: str
    label: str
    notes: str | None = None
    phase: str | None = None
    zone_id: str | None = None


class BeatsResponse(BaseModel):
    level_id: str
    spec_id: str
    nodes: list[BeatNode]


@router.get("/beats", response_model=BeatsResponse)
def get_beats(
    level_id: str,
    store: SpecStore = Depends(get_store),
):
    all_specs = store.list()
    bd_info = next(
        (s for s in all_specs if s.module == "bubble_diagram" and s.level_id == level_id),
        None,
    )
    if not bd_info:
        raise HTTPException(404, f"no bubble_diagram spec for level_id={level_id}")
    rec = store.get(bd_info.id)
    raw_nodes = rec.content.get("nodes", [])
    nodes = []
    for n in raw_nodes:
        if not isinstance(n, dict):
            continue
        nodes.append(BeatNode(
            id=n.get("id", ""),
            type=n.get("type", ""),
            label=n.get("label", ""),
            notes=n.get("notes"),
            phase=n.get("phase"),
            zone_id=n.get("zone_id"),
        ))
    return BeatsResponse(level_id=level_id, spec_id=bd_info.id, nodes=nodes)


@router.post("/compose-prompts", response_model=ComposeResponse)
def compose_prompts(
    body: ComposeRequest,
    store: SpecStore = Depends(get_store),
):
    try:
        rec = store.get(body.spec_id)
    except SpecNotFound:
        raise HTTPException(404, f"spec not found: {body.spec_id}")

    content = rec.content
    from tools.storyboard_render import PromptComposer

    composer = PromptComposer(content)
    neg = (content.get("style_anchor", {}).get("negative_prompt") or "").strip()
    panels = content.get("panels", [])

    items = []
    for p in panels:
        if not isinstance(p, dict):
            continue
        items.append(PromptItem(
            panel_id=p.get("panel_id", ""),
            title=p.get("title", ""),
            prompt=composer.compose(p),
            negative_prompt=neg,
        ))
    return ComposeResponse(panels=items)


@router.post("/upload-image", response_model=UploadResponse)
async def upload_image(
    spec_id: str,
    panel_id: str,
    file: UploadFile = File(...),
):
    s = get_settings()
    store: SpecStore = get_store()

    try:
        rec = store.get(spec_id)
    except SpecNotFound:
        raise HTTPException(404, f"spec not found: {spec_id}")

    level_id = rec.content.get("meta", {}).get("level_id", spec_id)
    original_name = file.filename or "image.png"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTS:
        raise HTTPException(400, f"不支持的图片格式 {suffix}，允许：{', '.join(sorted(ALLOWED_EXTS))}")

    assets_dir = s.project_root / "assets" / level_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    filename = f"storyboard_{panel_id}{suffix}"
    dest = assets_dir / filename

    total = 0
    with dest.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"图片过大（>{MAX_IMAGE_BYTES // (1024*1024)}MB）")
            f.write(chunk)

    relative_path = f"assets/{level_id}/{filename}"
    return UploadResponse(relative_path=relative_path, panel_id=panel_id)
