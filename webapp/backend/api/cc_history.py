"""历史 cc 对话恢复 API。

cc CLI 把每个 session 的完整 transcript 存到 ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
本模块负责扫描这些 jsonl 文件、解析、并允许 webapp 恢复某个历史 session 继续对话。
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import get_settings

router = APIRouter(prefix="/api/cc-history", tags=["cc-history"])


def _project_dir(project_root: Path) -> Path:
    """把项目绝对路径转成 cc 用的 ~/.claude/projects/ 子目录名。
    /Users/mofashu/Desktop/level-design-deck → -Users-mofashu-Desktop-level-design-deck
    """
    encoded = str(project_root).replace("/", "-")
    return Path.home() / ".claude" / "projects" / encoded


def _parse_message_brief(jsonl_path: Path) -> dict[str, Any]:
    """读 jsonl 头几行，拿首个有意义的 user 消息预览 + 消息计数。"""
    first_user = ""
    skill_hint = ""  # 如果首条是 skill 注入，记录 skill 名做 fallback
    user_count = 0
    assistant_count = 0
    import re
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = d.get("type")
                if t == "user":
                    user_count += 1
                    if not first_user:
                        msg = d.get("message", {})
                        content = msg.get("content", "")
                        if isinstance(content, list) and content:
                            content = content[0].get("text", "") if isinstance(content[0], dict) else ""
                        if not isinstance(content, str):
                            continue
                        preview = content.strip()
                        # 附件提示直接跳过
                        if preview.startswith("以下是用户附带的参考文件"):
                            continue
                        # skill 注入开头 → 抓 skill 名做 fallback，然后继续找下一条
                        if preview.startswith("# /"):
                            m = re.match(r"# (/[\w-]+)", preview)
                            if m and not skill_hint:
                                skill_hint = f"[skill] {m.group(1)}"
                            continue
                        first_user = preview[:80]
                elif t == "assistant":
                    assistant_count += 1
    except OSError:
        pass
    return {
        "first_user": first_user or skill_hint,
        "user_turns": user_count,
        "assistant_turns": assistant_count,
    }


class CcSessionBrief(BaseModel):
    cc_session_id: str
    mtime: float
    size_bytes: int
    first_user: str  # 首条非附件用户消息预览，最长 80 字
    user_turns: int
    assistant_turns: int


@router.get("", response_model=list[CcSessionBrief])
def list_cc_sessions(limit: int = 30, settings=Depends(get_settings)):
    """按 mtime 倒序列出最近的历史 session。limit 默认 30，足够下拉显示。"""
    project_dir = _project_dir(settings.project_root)
    if not project_dir.exists():
        return []
    files = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    out: list[CcSessionBrief] = []
    for p in files:
        stat = p.stat()
        brief = _parse_message_brief(p)
        # 过滤完全没用户消息的（队列管理类残留）
        if brief["user_turns"] == 0:
            continue
        out.append(CcSessionBrief(
            cc_session_id=p.stem,
            mtime=stat.st_mtime,
            size_bytes=stat.st_size,
            first_user=brief["first_user"],
            user_turns=brief["user_turns"],
            assistant_turns=brief["assistant_turns"],
        ))
    return out


class HistoryMessage(BaseModel):
    kind: str  # "user" | "assistant" | "tool_use" | "thinking"
    text: str
    ts: float | None = None
    tool: str | None = None  # only for tool_use


class GeneratedDoc(BaseModel):
    filename: str
    url: str            # /docs/<filename>
    exists: bool        # docs/ 下文件是否仍存在
    last_touched: float # 最后一次 Write/Edit 的 timestamp（毫秒）


@router.get("/{cc_session_id}/generated-docs", response_model=list[GeneratedDoc])
def get_generated_docs(cc_session_id: str, settings=Depends(get_settings)):
    """扫 transcript 里 AI Write/Edit 到 docs/*.html 的文件路径，
    返回最新的产物（去重，按最后接触时间倒序）。前端恢复 session 时用它自动打开预览。"""
    if "/" in cc_session_id or "\\" in cc_session_id or ".." in cc_session_id:
        raise HTTPException(400, "invalid cc_session_id")
    project_dir = _project_dir(settings.project_root)
    jsonl_path = project_dir / f"{cc_session_id}.jsonl"
    if not jsonl_path.exists():
        raise HTTPException(404, f"transcript not found: {cc_session_id}")

    docs_dir = settings.project_root / "docs"
    docs_root_str = str(docs_dir)
    touched: dict[str, float] = {}  # absolute path → last ts (ms)

    from datetime import datetime
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("type") != "assistant":
                    continue
                ts_str = d.get("timestamp")
                ts_ms = 0.0
                if isinstance(ts_str, str):
                    try:
                        ts_ms = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp() * 1000
                    except (ValueError, AttributeError):
                        pass
                blocks = d.get("message", {}).get("content", []) or []
                for b in blocks:
                    if b.get("type") != "tool_use":
                        continue
                    if b.get("name") not in ("Write", "Edit"):
                        continue
                    fp = b.get("input", {}).get("file_path", "")
                    if not isinstance(fp, str):
                        continue
                    if not fp.startswith(docs_root_str):
                        continue
                    if not fp.endswith(".html"):
                        continue
                    touched[fp] = max(touched.get(fp, 0), ts_ms)
    except OSError as e:
        raise HTTPException(500, f"read transcript failed: {e}")

    out: list[GeneratedDoc] = []
    for fp, ts in sorted(touched.items(), key=lambda kv: kv[1], reverse=True):
        p = Path(fp)
        out.append(GeneratedDoc(
            filename=p.name,
            url=f"/docs/{p.name}",
            exists=p.exists(),
            last_touched=ts,
        ))
    return out


@router.get("/{cc_session_id}/messages", response_model=list[HistoryMessage])
def get_history_messages(cc_session_id: str, settings=Depends(get_settings)):
    """解析单个 transcript，按 webapp chat 消息格式返回，前端直接 setState。"""
    if "/" in cc_session_id or "\\" in cc_session_id or ".." in cc_session_id:
        raise HTTPException(400, "invalid cc_session_id")
    project_dir = _project_dir(settings.project_root)
    jsonl_path = project_dir / f"{cc_session_id}.jsonl"
    if not jsonl_path.exists():
        raise HTTPException(404, f"transcript not found: {cc_session_id}")

    msgs: list[HistoryMessage] = []
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = d.get("type")
                ts_str = d.get("timestamp")
                ts = None
                if isinstance(ts_str, str):
                    # cc transcript 用 ISO 字符串
                    try:
                        from datetime import datetime
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp() * 1000
                    except (ValueError, AttributeError):
                        pass

                if t == "user":
                    msg = d.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, list) and content:
                        content = content[0].get("text", "") if isinstance(content[0], dict) else ""
                    if not isinstance(content, str) or not content.strip():
                        continue
                    # 跳过附件提示消息（前端不需要看见）
                    if content.startswith("以下是用户附带的参考文件"):
                        continue
                    msgs.append(HistoryMessage(kind="user", text=content, ts=ts))
                elif t == "assistant":
                    msg = d.get("message", {})
                    blocks = msg.get("content", []) or []
                    for b in blocks:
                        bt = b.get("type")
                        if bt == "text":
                            text = b.get("text", "")
                            if text.strip():
                                msgs.append(HistoryMessage(kind="assistant", text=text, ts=ts))
                        elif bt == "thinking":
                            text = b.get("thinking", "")
                            if text.strip():
                                msgs.append(HistoryMessage(kind="thinking", text=text, ts=ts))
                        elif bt == "tool_use":
                            tool_name = b.get("name", "?")
                            tool_input = b.get("input", {})
                            # tool 消息体简化为 JSON 字符串预览
                            text = json.dumps(tool_input, ensure_ascii=False)[:300]
                            msgs.append(HistoryMessage(kind="tool_use", text=text, ts=ts, tool=tool_name))
    except OSError as e:
        raise HTTPException(500, f"read transcript failed: {e}")

    return msgs
