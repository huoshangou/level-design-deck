"""FastAPI Depends() 工厂。

测试时 app.dependency_overrides[get_store] = lambda: fake_store 即可替换。
Phase 4 加 RemoteSpecStore 时只改 _make_store 一处。
"""

from __future__ import annotations
from functools import lru_cache

from backend.agent.base import AgentRunner
from backend.agent.local_cc import LocalCcRunner
from backend.config import Settings, load_settings
from backend.store.base import SpecStore
from backend.store.file_store import FileSpecStore


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


@lru_cache(maxsize=1)
def _make_store() -> SpecStore:
    return FileSpecStore(get_settings().project_root)


@lru_cache(maxsize=1)
def _make_agent() -> AgentRunner:
    s = get_settings()
    if s.agent_backend == "local":
        return LocalCcRunner(s.project_root, add_dirs=s.add_dirs)
    if s.agent_backend == "remote":
        from backend.agent.remote import RemoteAgentRunner
        return RemoteAgentRunner(
            gateway_url=s.remote_gateway_url,
            token=s.remote_gateway_token,
        )
    raise NotImplementedError(f"agent_backend={s.agent_backend!r} 不是合法值（local | remote）")


def get_store() -> SpecStore:
    return _make_store()


def get_agent() -> AgentRunner:
    return _make_agent()
