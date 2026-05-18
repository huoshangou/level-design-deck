"""Session management REST endpoints."""

from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.agent.base import AgentRunner
from backend.deps import get_agent

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    client_id: str | None = None
    namespace: str = "default"


class SessionResponse(BaseModel):
    client_id: str
    namespace: str
    started_at: float
    cc_session_id: str | None


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


@router.post("", response_model=SessionResponse, status_code=201)
def start_session(
    body: StartSessionRequest = StartSessionRequest(),
    agent: AgentRunner = Depends(get_agent),
):
    client_id = body.client_id or str(uuid.uuid4())
    try:
        meta = agent.start_session(client_id, body.namespace)
    except ValueError:
        raise HTTPException(409, f"session already exists: {client_id}")
    return SessionResponse(**meta)


@router.get("", response_model=SessionListResponse)
def list_sessions(agent: AgentRunner = Depends(get_agent)):
    return {"sessions": agent.list_sessions()}


@router.get("/{client_id}", response_model=SessionResponse)
def get_session(client_id: str, agent: AgentRunner = Depends(get_agent)):
    meta = agent.get_session(client_id)
    if meta is None:
        raise HTTPException(404, f"session not found: {client_id}")
    return SessionResponse(**meta)


@router.delete("/{client_id}")
def end_session(client_id: str, agent: AgentRunner = Depends(get_agent)):
    if not agent.has_session(client_id):
        raise HTTPException(404, f"session not found: {client_id}")
    agent.end_session(client_id)
    # 顺便清理上传附件
    from backend.api.files import clear_session_files
    clear_session_files(client_id)
    return {"ok": True}
