"""AgentRunner ABC + 事件协议。

Phase 2 默认实现 = LocalCcRunner（subprocess + claude CLI stream-json）。
Phase 4 可加 RemoteAgentRunner（HTTP/SSE 调工具组 gateway），签名不变。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator

from backend.agent.events import AgentEvent


class AgentRunner(ABC):
    @abstractmethod
    def start_session(self, client_id: str, namespace: str = "default") -> dict:
        """注册新 session。立刻返回（不调 cc），cc session_id 在第一次 send_message 时 lazy 拿到。

        Returns: {client_id, namespace, started_at, cc_session_id: None}
        """

    @abstractmethod
    def has_session(self, client_id: str) -> bool: ...

    @abstractmethod
    def get_session(self, client_id: str) -> dict | None: ...

    @abstractmethod
    def list_sessions(self) -> list[dict]: ...

    @abstractmethod
    def end_session(self, client_id: str) -> None: ...

    @abstractmethod
    def send_message(self, client_id: str, text: str) -> AsyncIterator[AgentEvent]:
        """向 cc 发用户消息，async 流出事件序列。"""
