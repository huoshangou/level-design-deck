"""mechanical_check + template_diff + cross_check endpoint。"""

from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import get_store
from backend.services.check_service import run_check
from backend.services.cross_check_service import run_cross
from backend.store.base import SpecNotFound, SpecStore

router = APIRouter(prefix="/api", tags=["check"])


class CheckRequest(BaseModel):
    spec_id: str
    namespace: str = "default"


class CrossCheckRequest(BaseModel):
    level_id: str


@router.post("/check")
def check_spec(
    body: CheckRequest,
    store: SpecStore = Depends(get_store),
) -> dict[str, Any]:
    try:
        rec = store.get(body.spec_id, body.namespace)
    except SpecNotFound:
        raise HTTPException(404, f"spec not found: {body.spec_id}")
    return run_check(rec)


@router.post("/cross-check")
def cross_check(body: CrossCheckRequest) -> dict[str, Any]:
    return run_cross(body.level_id)
