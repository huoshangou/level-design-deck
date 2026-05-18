"""pytest fixtures。"""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.config import PROJECT_ROOT


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def cleanup_smoke_specs():
    """yield 后清理 specs/test_smoke_*.spec.json，避免污染真实数据。"""
    yield
    for p in (PROJECT_ROOT / "specs").glob("test_smoke_*.spec.json"):
        p.unlink()
