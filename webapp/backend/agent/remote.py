"""RemoteAgentRunner — Phase 4 stub。

工具组接管时替换此文件的方法实现。ABC 签名与 LocalCcRunner 完全一致，
业务层（api/sessions.py、api/chat.py）无需改动。

部署拓扑（工具组实现时参考）：
  browser → FastAPI daemon → RemoteAgentRunner
                              ↓ HTTP/SSE
                          远端 gateway（工具组运营）
                              ↓
                          cc 池（多用户隔离，按 namespace 路由）

认证方案 sketch（Phase 4 待实现）：
  - 请求头 Authorization: Bearer <token>
  - FastAPI middleware 验 token → 注入 request.state.namespace
  - RemoteAgentRunner 所有方法带 namespace 参数（已在 ABC 定义）
"""

from __future__ import annotations
from typing import AsyncIterator

from backend.agent.base import AgentRunner
from backend.agent.events import AgentEvent


class RemoteAgentRunner(AgentRunner):
    """Phase 4 远端 AgentRunner stub。所有方法未实现，均抛 NotImplementedError。"""

    def __init__(self, gateway_url: str, token: str | None = None):
        """
        Args:
            gateway_url: 工具组 gateway 基地址，如 "https://cc-gateway.internal"
            token: Bearer token（可空，开发期可用无认证模式）
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.token = token

    def start_session(self, client_id: str, namespace: str = "default") -> dict:
        raise NotImplementedError(
            "RemoteAgentRunner.start_session — Phase 4 待工具组实现。"
            f" (client_id={client_id!r}, namespace={namespace!r})"
        )

    def has_session(self, client_id: str) -> bool:
        raise NotImplementedError("RemoteAgentRunner.has_session — Phase 4 stub")

    def get_session(self, client_id: str) -> dict | None:
        raise NotImplementedError("RemoteAgentRunner.get_session — Phase 4 stub")

    def list_sessions(self) -> list[dict]:
        raise NotImplementedError("RemoteAgentRunner.list_sessions — Phase 4 stub")

    def end_session(self, client_id: str) -> None:
        raise NotImplementedError("RemoteAgentRunner.end_session — Phase 4 stub")

    def interrupt(self, client_id: str) -> bool:
        raise NotImplementedError(
            "RemoteAgentRunner.interrupt — Phase 4 stub。"
            " 预期协议：POST {gateway}/sessions/{client_id}/interrupt（或者 WS 端推 cancel 帧给 gateway）"
        )

    async def send_message(self, client_id: str, text: str) -> AsyncIterator[AgentEvent]:
        raise NotImplementedError(
            "RemoteAgentRunner.send_message — Phase 4 待工具组实现。"
            " 预期协议：POST {gateway}/sessions/{client_id}/messages → SSE stream，"
            " 每条 SSE data 对应一个 AgentEvent JSON，type 字段同 events.py 定义。"
        )
        # type-checker 需要 yield 让函数成为 AsyncGenerator
        yield  # type: ignore[misc]
