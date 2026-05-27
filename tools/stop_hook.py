#!/usr/bin/env python3
"""
stop_hook.py — LDD 对话结束自动落盘 [决策]/[待定]/[风险]/[需求]/[迭代] 标记

cc Stop 事件触发，从 stdin 读 payload `{session_id, transcript_path, cwd}`，
扫 transcript 最后 60 条消息抽含设计标记的片段，追加到
`memory/pending_review.md`。下次 session 启动时由 CLAUDE.md 引导合并。

约束（详见 CLAUDE.md）：
- stdlib only（json + re + sys + pathlib + datetime）
- < 200 行
- 跨平台（macOS / Linux / Windows WSL2）
- silent fail（不阻塞 cc Stop 流程）

参考：projectx-leveldesign scripts/stop_hook.py 的 line_is_real_marker / strip_code_contexts
逻辑（重写为 LDD 风格 — 追加写、无 debug log、无 WSL 硬编码）
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

DESIGN_MARKERS = ["[决策]", "[待定]", "[风险]", "[需求]", "[迭代]"]

CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

# 单次 transcript 解析行数上限（防 transcript 过大爆炸）
MAX_RECENT_MSGS = 60
# pending_review.md 单次写入字符上限
MAX_WRITE_BYTES = 50 * 1024


def project_root() -> Path:
    """cc Code 注入 CLAUDE_PROJECT_DIR，否则回退到 cwd。"""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path.cwd()


def is_ldd_cwd(cwd: str) -> bool:
    """只在 LDD 工作目录触发（防止 cc 在别处也写 LDD memory）。"""
    if not cwd:
        return False
    try:
        cp = Path(cwd).resolve()
    except OSError:
        return False
    root = project_root().resolve()
    return cp == root or root in cp.parents or cp in root.parents


def read_transcript(path: str) -> list[dict]:
    """读 transcript JSONL，逐行解析。"""
    p = Path(path)
    if not p.exists():
        return []
    msgs = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    msgs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return msgs


def extract_text(content) -> str:
    """从 message.content 抽文本。content 可能是 str 或 [{type, text}] 数组。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return ""


def message_text(record: dict) -> str:
    msg = record.get("message", {})
    if isinstance(msg, dict):
        return extract_text(msg.get("content", ""))
    return ""


def strip_code(text: str) -> str:
    """移除代码块 / 行内代码（避免假阳性标记）。"""
    text = CODE_BLOCK_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def is_real_marker_line(line: str) -> bool:
    """某行含真标记 + 后跟 > 5 字符实质内容。"""
    stripped = line.strip()
    if stripped.startswith("```"):
        return False
    for marker in DESIGN_MARKERS:
        if marker in stripped:
            after = stripped[stripped.index(marker) + len(marker):].strip()
            if len(after) > 5:
                return True
    return False


def collect_marker_lines(messages: list[dict]) -> list[tuple[str, str]]:
    """返回 [(role, line)] 列表，按出现顺序。"""
    recent = messages[-MAX_RECENT_MSGS:]
    out = []
    for rec in recent:
        role = rec.get("type", "?")
        raw = message_text(rec)
        if not raw:
            continue
        clean = strip_code(raw)
        if not any(m in clean for m in DESIGN_MARKERS):
            continue
        for ln in clean.splitlines():
            if is_real_marker_line(ln):
                out.append((role, ln.strip()))
    return out


def append_pending_review(marker_lines: list[tuple[str, str]], session_id: str,
                          cwd: str, transcript_path: str) -> None:
    """追加到 memory/pending_review.md。"""
    if not marker_lines:
        return

    root = project_root()
    mem_dir = root / "memory"
    mem_dir.mkdir(exist_ok=True)
    target = mem_dir / "pending_review.md"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sid_short = session_id[:8] if session_id else "?"

    header = []
    if not target.exists() or target.stat().st_size == 0:
        # 首次创建文件，写表头说明
        header = [
            "# pending_review.md — Stop Hook 自动落盘\n",
            "\n",
            "> 由 `tools/stop_hook.py` 在 cc 对话结束时追加。Session 启动时由\n",
            "> CLAUDE.md 引导你跟 Steve 确认合并到正式位置（PROJECT.md 决策记录、\n",
            "> 某 module spec 备注、CLAUDE.md 约束清单等）后清空对应段。\n",
            "\n",
            "---\n",
        ]

    body = [f"\n## {now}  session={sid_short}\n\n"]
    body.append(f"- transcript: `{transcript_path}`\n")
    body.append(f"- cwd: `{cwd}`\n")
    body.append("\n")
    for role, line in marker_lines:
        # role 标识：user → 👤 / assistant → 🤖 / 其他 → ·
        icon = {"user": "👤", "assistant": "🤖"}.get(role, "·")
        body.append(f"- {icon} {line}\n")

    payload = "".join(header) + "".join(body)
    if len(payload.encode("utf-8")) > MAX_WRITE_BYTES:
        # 截断 + 加提示
        payload = payload[: MAX_WRITE_BYTES // 2] + \
            "\n\n[...截断 — 单次写入超 50KB，剩余请回看 transcript]\n"

    try:
        with target.open("a", encoding="utf-8") as f:
            f.write(payload)
    except OSError:
        return


def main() -> int:
    """silent fail：任何异常 exit 0 不阻塞 cc Stop 流程。"""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return 0

    cwd = payload.get("cwd", "")
    if not is_ldd_cwd(cwd):
        return 0

    transcript_path = payload.get("transcript_path", "")
    session_id = payload.get("session_id", "")
    if not transcript_path:
        return 0

    try:
        msgs = read_transcript(transcript_path)
        if not msgs:
            return 0
        marker_lines = collect_marker_lines(msgs)
        append_pending_review(marker_lines, session_id, cwd, transcript_path)
    except Exception:
        # 严格 silent fail：任何错都不阻塞 cc
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
