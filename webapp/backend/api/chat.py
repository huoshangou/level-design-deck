"""Chat endpoints: POST /messages (trigger) + WS /ws/chat/{client_id} (event stream)."""

from __future__ import annotations
import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.agent.base import AgentRunner
from backend.agent.events import event_to_dict
from backend.api.files import get_attached_files
from backend.deps import get_agent

router = APIRouter(tags=["chat"])

# client_id → asyncio.Queue[str]  (populated by POST, consumed by WS handler)
_queues: dict[str, asyncio.Queue] = {}

# client_id → bool  (True while a WS is connected)
_ws_connected: dict[str, bool] = {}


class SendMessageRequest(BaseModel):
    text: str


@router.post("/api/sessions/{client_id}/messages", status_code=202)
def send_message(
    client_id: str,
    body: SendMessageRequest,
    agent: AgentRunner = Depends(get_agent),
):
    if not agent.has_session(client_id):
        raise HTTPException(404, f"session not found: {client_id}")
    if not _ws_connected.get(client_id):
        raise HTTPException(409, "no active websocket connection — connect WS first")

    from backend.api.profile import profile_prompt_block
    profile_block = profile_prompt_block()

    text = body.text
    readable = [a for a in get_attached_files(client_id) if a.get("text_path")]
    if readable:
        paths = "\n".join(
            f"- {a['text_path']}  (原文件: {a['original_name']})" for a in readable
        )
        text = (
            "以下是用户附带的参考文件，你可以用 Read 工具按需读取这些路径：\n"
            f"{paths}\n\n用户问题：{body.text}"
        )
    if profile_block:
        text = profile_block + text
    _queues[client_id].put_nowait(text)
    return {"queued": True}


def _make_envelope(ev_dict: dict, client_id: str) -> str:
    envelope: dict[str, Any] = {
        "type": ev_dict.get("type"),
        "ts": time.time(),
        "client_id": client_id,
        "payload": ev_dict,
    }
    return json.dumps(envelope, ensure_ascii=False)


@router.websocket("/ws/chat/{client_id}")
async def ws_chat(websocket: WebSocket, client_id: str):
    agent: AgentRunner = get_agent()

    if not agent.has_session(client_id):
        await websocket.close(code=4404)
        return

    await websocket.accept()

    queue: asyncio.Queue = asyncio.Queue()
    _queues[client_id] = queue
    _ws_connected[client_id] = True

    try:
        while True:
            recv_task = asyncio.create_task(websocket.receive_text())
            queue_task = asyncio.create_task(queue.get())

            done, pending = await asyncio.wait(
                {recv_task, queue_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for t in pending:
                t.cancel()

            if recv_task in done:
                try:
                    raw = recv_task.result()
                except WebSocketDisconnect:
                    break
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    msg = {}
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                # "interrupt" — v1 stub: received, not acted on

            if queue_task in done:
                text = queue_task.result()
                async for ev in agent.send_message(client_id, text):
                    ev_dict = event_to_dict(ev)
                    await websocket.send_text(_make_envelope(ev_dict, client_id))

    except WebSocketDisconnect:
        pass
    finally:
        _ws_connected.pop(client_id, None)
        _queues.pop(client_id, None)
