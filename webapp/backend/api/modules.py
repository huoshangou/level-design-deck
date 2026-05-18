"""Module 元数据 endpoint：列 module、读 schema、兼容老 /api/paths。"""

from __future__ import annotations
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.deps import get_settings
from backend.services.generate_service import list_modules

router = APIRouter(prefix="/api", tags=["modules"])


class ModuleInfo(BaseModel):
    name: str
    schema_path: str | None
    demo_path: str | None
    lvm_generated: bool
    spec_id_pattern: str | None


class ModuleListResponse(BaseModel):
    modules: list[ModuleInfo]


class PathsResponse(BaseModel):
    spec: str
    schema_path: str
    template: str


@router.get("/modules", response_model=ModuleListResponse)
def get_modules():
    return {"modules": [ModuleInfo(**m) for m in list_modules()]}


@router.get("/modules/{name}/schema")
def get_module_schema(name: str) -> dict[str, Any]:
    schema_path = get_settings().project_root / "schema" / f"{name}.schema.json"
    if not schema_path.exists():
        raise HTTPException(404, f"schema not found for module={name!r}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


@router.get("/paths", response_model=PathsResponse)
def resolve_paths(spec: str = Query(..., description="spec_id（不含 .spec.json）")):
    """兼容旧 serve_editor 的 /api/paths?spec=X 端点。"""
    root = get_settings().project_root
    schema_dir = root / "schema"
    candidates = sorted(
        (p.name[:-len(".schema.json")] for p in schema_dir.glob("*.schema.json")),
        key=len, reverse=True,
    )
    for module in candidates:
        if module in spec:
            return PathsResponse(
                spec=f"specs/{spec}.spec.json",
                schema_path=f"schema/{module}.schema.json",
                template=f"templates/{module}.html.tmpl",
            )
    raise HTTPException(404, f"cannot infer module for spec_id={spec!r}")
