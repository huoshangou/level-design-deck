"""Session REST endpoint tests — uses FakeAgent (no real cc)."""

from __future__ import annotations
import time
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from backend.agent.base import AgentRunner
from backend.agent.events import AgentEvent
from backend.app import app
from backend.deps import get_agent


class FakeAgent(AgentRunner):
    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def start_session(self, client_id: str, namespace: str = "default") -> dict:
        if client_id in self._sessions:
            raise ValueError(f"session already exists: {client_id}")
        meta = {
            "client_id": client_id,
            "namespace": namespace,
            "cc_session_id": None,
            "started_at": time.time(),
            "last_active": None,
            "turn_count": 0,
        }
        self._sessions[client_id] = meta
        return dict(meta)

    def has_session(self, client_id: str) -> bool:
        return client_id in self._sessions

    def get_session(self, client_id: str) -> dict | None:
        m = self._sessions.get(client_id)
        return dict(m) if m else None

    def list_sessions(self) -> list[dict]:
        return [dict(m) for m in self._sessions.values()]

    def end_session(self, client_id: str) -> None:
        self._sessions.pop(client_id, None)

    async def send_message(self, client_id: str, text: str) -> AsyncIterator[AgentEvent]:
        return
        yield  # make it an async generator


@pytest.fixture
def fake_agent():
    agent = FakeAgent()
    app.dependency_overrides[get_agent] = lambda: agent
    yield agent
    app.dependency_overrides.pop(get_agent, None)


@pytest.fixture
def sessions_client(fake_agent):
    return TestClient(app)


def test_post_session_auto_id(sessions_client, fake_agent):
    r = sessions_client.post("/api/sessions", json={"namespace": "test"})
    assert r.status_code == 201
    d = r.json()
    assert d["namespace"] == "test"
    assert d["cc_session_id"] is None
    assert d["started_at"] > 0
    assert len(d["client_id"]) > 0


def test_post_session_explicit_id(sessions_client, fake_agent):
    r = sessions_client.post("/api/sessions", json={"client_id": "explicit-123"})
    assert r.status_code == 201
    assert r.json()["client_id"] == "explicit-123"


def test_post_session_duplicate_409(sessions_client, fake_agent):
    sessions_client.post("/api/sessions", json={"client_id": "dup-id"})
    r = sessions_client.post("/api/sessions", json={"client_id": "dup-id"})
    assert r.status_code == 409


def test_get_session_ok(sessions_client, fake_agent):
    sessions_client.post("/api/sessions", json={"client_id": "get-me"})
    r = sessions_client.get("/api/sessions/get-me")
    assert r.status_code == 200
    assert r.json()["client_id"] == "get-me"


def test_get_session_404(sessions_client, fake_agent):
    r = sessions_client.get("/api/sessions/no-such-session-xyz")
    assert r.status_code == 404


def test_delete_session_ok(sessions_client, fake_agent):
    sessions_client.post("/api/sessions", json={"client_id": "del-me"})
    r = sessions_client.delete("/api/sessions/del-me")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    r2 = sessions_client.get("/api/sessions/del-me")
    assert r2.status_code == 404


def test_delete_session_404(sessions_client, fake_agent):
    r = sessions_client.delete("/api/sessions/ghost-session-xyz")
    assert r.status_code == 404


def test_list_sessions(sessions_client, fake_agent):
    sessions_client.post("/api/sessions", json={"client_id": "list-a"})
    sessions_client.post("/api/sessions", json={"client_id": "list-b"})
    r = sessions_client.get("/api/sessions")
    assert r.status_code == 200
    ids = {s["client_id"] for s in r.json()["sessions"]}
    assert {"list-a", "list-b"} <= ids
