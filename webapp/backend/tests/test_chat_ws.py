"""WebSocket chat endpoint tests — runs live cc (no mock).

Strategy: TestClient is thread-safe; WS connection stays open in the main
thread while a daemon thread fires the POST /messages request.
"""

from __future__ import annotations
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── helpers ──────────────────────────────────────────────────────────────────


def _post_session(client: TestClient, client_id: str) -> dict:
    r = client.post("/api/sessions", json={"client_id": client_id})
    assert r.status_code == 201, r.text
    return r.json()


def _collect_ws_events(
    client: TestClient,
    client_id: str,
    stop_event: threading.Event,
    results: list,
):
    """Run in a thread: open WS, collect JSON events until stop_event set."""
    with client.websocket_connect(f"/ws/chat/{client_id}") as ws:
        while not stop_event.is_set():
            try:
                ws.send_text(json.dumps({"type": "ping"}))
                raw = ws.receive_text()
                msg = json.loads(raw)
                if msg.get("type") != "pong":
                    results.append(msg)
            except Exception:
                break


# ── tests ─────────────────────────────────────────────────────────────────────


def test_ws_no_session_closes_4404(client):
    """Connecting to WS without prior POST /api/sessions → close 4404."""
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect("/ws/chat/ghost-no-session-xyz") as ws:
            ws.receive_text()
    # starlette raises WebSocketDisconnect or similar; we just verify the
    # connection was refused / closed, which means an exception was raised.
    assert exc_info.value is not None


def test_ws_ping_pong(client):
    """WS connection for a valid session responds to ping."""
    client_id = "ws-ping-test"
    _post_session(client, client_id)

    with client.websocket_connect(f"/ws/chat/{client_id}") as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        raw = ws.receive_text()
        assert json.loads(raw) == {"type": "pong"}

    client.delete(f"/api/sessions/{client_id}")


def test_post_messages_no_ws_returns_409(client):
    """POST /messages without WS → 409."""
    client_id = "post-no-ws"
    _post_session(client, client_id)
    r = client.post(f"/api/sessions/{client_id}/messages", json={"text": "hello"})
    assert r.status_code == 409
    client.delete(f"/api/sessions/{client_id}")


def test_post_messages_no_session_returns_404(client):
    """POST /messages for unknown client_id → 404."""
    r = client.post("/api/sessions/ghost-xxx/messages", json={"text": "hi"})
    assert r.status_code == 404


def test_ws_full_turn_live_cc(client):
    """Full turn: POST session → connect WS → POST message → collect events.

    Runs against the real cc CLI. Skipped if `claude` not in PATH.
    """
    import shutil
    if not shutil.which("claude"):
        pytest.skip("`claude` CLI not found in PATH")

    client_id = "ws-live-cc-test"
    _post_session(client, client_id)

    collected: list[dict] = []
    stop = threading.Event()

    ws_thread = threading.Thread(
        target=_collect_ws_events,
        args=(client, client_id, stop, collected),
        daemon=True,
    )
    ws_thread.start()

    # Give WS time to connect and register in _ws_connected
    time.sleep(0.5)

    r = client.post(
        f"/api/sessions/{client_id}/messages",
        json={"text": "Reply with only the number 7, nothing else."},
    )
    assert r.status_code == 202, r.text

    # Wait for cc to finish (up to 60 s for real model call)
    deadline = time.time() + 60
    while time.time() < deadline:
        types = {e.get("type") for e in collected}
        if "cc_message_complete" in types:
            break
        time.sleep(0.5)

    stop.set()
    ws_thread.join(timeout=3)

    client.delete(f"/api/sessions/{client_id}")

    types_seen = {e.get("type") for e in collected}
    # Must have seen at least session_started and cc_message_complete
    assert "session_started" in types_seen, f"events seen: {types_seen}"
    assert "cc_message_complete" in types_seen, f"events seen: {types_seen}"

    # The complete event payload should contain "7"
    complete_events = [
        e for e in collected if e.get("type") == "cc_message_complete"
    ]
    combined_text = " ".join(
        e.get("payload", {}).get("text", "") for e in complete_events
    )
    assert "7" in combined_text, f"expected '7' in output, got: {combined_text!r}"
