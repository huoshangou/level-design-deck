"""Agent 事件类型，v1 给 WebSocket / 内部消费。

设计原则：每个事件独立 dataclass + Union 导出；前端按 .type 字段判别。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Union


@dataclass
class SessionStarted:
    client_id: str
    cc_session_id: str | None  # cc init 后 lazy 填，第一条消息前为 None
    type: str = "session_started"


@dataclass
class CcOutputDelta:
    """cc 文字输出。当前 CLI 是 turn-level（不是 token-level），整段一次。"""
    text: str
    message_id: str | None = None
    type: str = "cc_output_delta"


@dataclass
class CcThinking:
    """cc 思考块（haiku/sonnet thinking）。前端可折叠显示。"""
    text: str
    type: str = "cc_thinking"


@dataclass
class ToolUseStart:
    tool: str           # "Read" / "Write" / "Bash" / "Edit" / ...
    args: dict[str, Any]
    tool_use_id: str
    type: str = "tool_use_start"


@dataclass
class ToolUseEnd:
    tool: str
    tool_use_id: str
    ok: bool
    summary: str | None = None
    type: str = "tool_use_end"


@dataclass
class CcMessageComplete:
    """assistant turn 完成（cc result message）。含 cost / duration 元数据。"""
    text: str
    role: str = "assistant"
    cost_usd: float | None = None
    duration_ms: int | None = None
    cc_session_id: str | None = None
    type: str = "cc_message_complete"


@dataclass
class SpecUpdated:
    """spec 文件变化（来自 Watcher 或 cc Write 后）。前端 invalidate Query。"""
    spec_id: str
    mtime: float
    source: str = "agent"  # "agent" | "user" | "external"
    type: str = "spec_updated"


@dataclass
class AgentError:
    code: str
    message: str
    recoverable: bool = True
    type: str = "agent_error"


@dataclass
class SessionEnded:
    reason: str
    type: str = "session_ended"


@dataclass
class CcInterrupted:
    """用户主动 stop 当前 turn 时发出。区别于 AgentError —— 这不是错误，是受控终止。"""
    cc_session_id: str | None = None
    type: str = "cc_interrupted"


AgentEvent = Union[
    SessionStarted, CcOutputDelta, CcThinking, ToolUseStart, ToolUseEnd,
    CcMessageComplete, SpecUpdated, AgentError, SessionEnded, CcInterrupted,
]


def event_to_dict(ev: AgentEvent) -> dict:
    """dataclass → JSON-able dict，给 WebSocket envelope 用。"""
    from dataclasses import asdict
    d = asdict(ev)
    return d
