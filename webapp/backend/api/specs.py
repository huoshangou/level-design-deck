"""Spec CRUD endpoint。"""

from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.deps import get_store
from backend.store.base import SpecInvalid, SpecNotFound, SpecStore

router = APIRouter(prefix="/api/specs", tags=["specs"])


class SpecInfoModel(BaseModel):
    id: str
    module: str | None
    level_id: str | None
    mtime: float


class SpecListResponse(BaseModel):
    specs: list[SpecInfoModel]


class SpecRecordModel(BaseModel):
    id: str
    content: dict[str, Any]
    mtime: float
    module: str | None
    level_id: str | None


class SaveSpecRequest(BaseModel):
    content: dict[str, Any]


class SaveSpecResponse(BaseModel):
    id: str
    mtime: float


@router.get("", response_model=SpecListResponse)
def list_specs(
    namespace: str = Query("default"),
    store: SpecStore = Depends(get_store),
):
    items = store.list(namespace)
    return {"specs": [SpecInfoModel(**vars(s)) for s in items]}


@router.get("/{spec_id}", response_model=SpecRecordModel)
def get_spec(
    spec_id: str,
    namespace: str = Query("default"),
    store: SpecStore = Depends(get_store),
):
    try:
        rec = store.get(spec_id, namespace)
    except SpecNotFound:
        raise HTTPException(404, f"spec not found: {spec_id}")
    except SpecInvalid as e:
        raise HTTPException(400, str(e))
    return SpecRecordModel(**vars(rec))


@router.put("/{spec_id}", response_model=SaveSpecResponse)
def save_spec(
    spec_id: str,
    body: SaveSpecRequest,
    namespace: str = Query("default"),
    store: SpecStore = Depends(get_store),
):
    try:
        r = store.save(spec_id, body.content, namespace)
    except SpecInvalid as e:
        raise HTTPException(400, str(e))
    return SaveSpecResponse(id=r.id, mtime=r.mtime)


@router.delete("/{spec_id}")
def delete_spec(
    spec_id: str,
    namespace: str = Query("default"),
    store: SpecStore = Depends(get_store),
):
    try:
        store.delete(spec_id, namespace)
    except SpecNotFound:
        raise HTTPException(404, f"spec not found: {spec_id}")
    return {"ok": True}
