"""LocalCcRunner: subprocess + `claude` CLI stream-json bidirectional。

为什么不用 claude-agent-sdk：实测 SDK 0.2.82 与当前 cc CLI 2.1.122 协议不兼容
（SDK 期望 0.2.120 未发布），直接走 CLI 子进程更稳。

每次 send_message spawn 一个 cc 进程；用 --resume <cc_session_id> 保持上下文。
"""

from __future__ import annotations
import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncIterator, Sequence

from backend.agent.base import AgentRunner
from backend.agent.events import (
    AgentError, AgentEvent, CcInterrupted, CcMessageComplete, CcOutputDelta,
    CcThinking, SessionStarted, ToolUseStart,
)

DEFAULT_MODEL = "claude-haiku-4-5"

_LDD_SYSTEM_CONTEXT = (
    "你是 level-design-deck (LDD) 项目的内嵌助手。\n"
    "本项目用 spec.json 作为真源，HTML 是派生物。\n\n"
    "## 可用 module 类型（共 9 种）\n"
    "level_overview, spatial_layout, bubble_diagram, storyboard, "
    "atmosphere_ref, lighting_req, vfx_req, audio_req, asset_list\n\n"
    "## spec 文件位置\n"
    "所有 spec 存放在 specs/ 目录，命名 specs/<module>_<level_short_name>.spec.json\n"
    "每个 spec 的 JSON schema 在 schema/<module>.schema.json\n\n"
    "## 如何操作 spec\n"
    "- 查看：用 Read 工具读取 specs/<spec_id>.spec.json\n"
    "- 修改：用 Edit 工具修改 specs/<spec_id>.spec.json 中的具体字段\n"
    "- 新建：用 Read 工具读取对应 schema，按 schema 创建最小骨架，"
    "用 Write 工具写入 specs/ 目录\n"
    "- 渲染：用 Bash 跑 python3 tools/render.py specs/<spec_id>.spec.json\n\n"
    "## 注意事项\n"
    "- 不要推荐用户使用 pencil、Figma 等外部编辑器来编辑 spec\n"
    "- storyboard 的操作全在本 webapp 内完成（素材导入、节点映射、prompt 生成）\n"
    "- spatial_layout 的 2D 编辑使用内置的 LevelCraft 编辑器\n"
    "- bubble_diagram 在本 webapp 内通过 SchemaForm 编辑\n"
    "- 修改 spec 字段时只改需要的部分，保持其他内容不变\n"
)

# Phase 3 工具白名单：
# - Read / Glob / Grep：探索文件
# - Edit：原位修改 specs / docs / templates 内容
# - Write(specs/*) / Write(docs/*)：限制写入目录，防止 cc 写 ~/.claude/memory 等
# - Bash(python3 tools/*)：跑项目内生成脚本
# - Bash(python3 <DECK_EXTRACTOR_SCRIPTS>/*)：跑用户脚本（pdf2text / xlsx2text 等提取器）
#   默认 ~/scripts；env var DECK_EXTRACTOR_SCRIPTS 可覆盖（Windows 同事按需配）
# - Bash(ls *) / Bash(cp *)：列目录、复制模板
# 若环境变量 DECK_WRITE_TOOLS=0 则退回 Read-only（Phase 2 行为）
_READ_ONLY_TOOLS = ["Read", "Glob", "Grep"]


def _resolve_extractor_scripts_dir() -> str:
    """提取脚本目录（pdf2text 等）。优先 env var，否则 ~/scripts。"""
    from pathlib import Path
    v = os.environ.get("DECK_EXTRACTOR_SCRIPTS")
    if v:
        return v
    return str(Path.home() / "scripts")


def _build_write_allowed_tools() -> list[str]:
    extractor_dir = _resolve_extractor_scripts_dir()
    return [
        "Read", "Glob", "Grep", "Edit",
        "Write(specs/*)", "Write(docs/*)",
        "Bash(python3 tools/*)",
        f"Bash(python3 {extractor_dir}/*)",
        "Bash(ls *)",
        "Bash(cp *)",
    ]


def _resolve_allowed_tools() -> Sequence[str]:
    """读环境变量决定工具白名单。DECK_WRITE_TOOLS=0 → read-only；否则 Phase 3 完整白名单。"""
    if os.environ.get("DECK_WRITE_TOOLS", "1") == "0":
        return _READ_ONLY_TOOLS
    return _build_write_allowed_tools()


class LocalCcRunner(AgentRunner):
    def __init__(
        self,
        project_root: Path,
        default_model: str = DEFAULT_MODEL,
        add_dirs: tuple[Path, ...] = (),
    ):
        self.project_root = Path(project_root)
        self.default_model = default_model
        self.add_dirs = add_dirs
        self._sessions: dict[str, dict] = {}
        self._allowed_tools: Sequence[str] = _resolve_allowed_tools()

    def start_session(self, client_id: str, namespace: str = "default", cc_session_id: str | None = None) -> dict:
        if client_id in self._sessions:
            raise ValueError(f"session already exists: {client_id}")
        meta = {
            "client_id": client_id,
            "namespace": namespace,
            "cc_session_id": cc_session_id,
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

    def interrupt(self, client_id: str) -> bool:
        """杀掉 client_id 当前活跃的 cc 子进程（如果有）。"""
        meta = self._sessions.get(client_id)
        if not meta:
            return False
        proc = meta.get("proc")
        if proc is None or proc.returncode is not None:
            return False
        meta["interrupted"] = True
        try:
            proc.terminate()
        except ProcessLookupError:
            return False
        return True

    async def send_message(self, client_id: str, text: str) -> AsyncIterator[AgentEvent]:
        if client_id not in self._sessions:
            yield AgentError(code="session_not_found", message=f"client_id={client_id}", recoverable=False)
            return

        meta = self._sessions[client_id]
        meta["interrupted"] = False  # 每个 turn 重置 flag，不让上一次的 interrupt 残留
        cc_sid = meta.get("cc_session_id")
        is_first_turn = cc_sid is None

        # Claude Code CLI 跨平台路径解析：
        # - Linux/macOS：通常 /usr/local/bin/claude（exe），直接 spawn
        # - Windows：npm shim 是 .cmd / .bat，Python subprocess 默认只搜 .exe，
        #   且 CreateProcess API 不接受 .cmd —— 必须 cmd.exe /c 包一层
        import shutil, sys, re
        claude_bin = shutil.which("claude") or "claude"
        use_shell = sys.platform == "win32" and claude_bin.lower().endswith((".cmd", ".bat"))

        cmd = [
            claude_bin, "--print",
            "--output-format=stream-json",
            "--input-format=stream-json",
            "--verbose",
            "--model", self.default_model,
            "--permission-mode", "acceptEdits",
            "--allowed-tools", *self._allowed_tools,
            "--append-system-prompt", _LDD_SYSTEM_CONTEXT,
        ]
        for d in self.add_dirs:
            cmd.extend(["--add-dir", str(d)])
        if cc_sid:
            cmd.extend(["--resume", cc_sid])

        env = os.environ.copy()
        env.pop("CLAUDE_CODE_ENTRYPOINT", None)
        # ANTHROPIC_* pop 策略按平台分：
        # - mac/linux：cc CLI 有 ~/.claude/.credentials.json 兜底，pop 后走 keychain
        #   认证；不 pop 反而可能被父进程错的 BASE_URL（如老 yotta gateway）污染。
        # - windows：cc CLI 完全靠 env var 认证（无 keychain 等价物），pop 后直接
        #   "not logged in"，必须保留继承。
        if sys.platform != "win32":
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("ANTHROPIC_BASE_URL", None)
            env.pop("ANTHROPIC_CUSTOM_HEADERS", None)
        # Clash Verge 等代理客户端会调 launchctl setenv 把 *_PROXY 写进全局 launchd env，
        # 双击 .command 启动的 webapp 会继承。yotta 公司网关只接受国内出口 IP，
        # 一旦走 clash 国外节点就被网关拒绝、cc 子进程在 kevent64 死等。
        # 这里整组剥掉，让 cc 子进程一律直连。详见 2026-05-21 调试。
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                  "http_proxy", "https_proxy", "all_proxy"):
            env.pop(k, None)

        try:
            # limit=10MB: cc 的 tool_result 含读到的整个文件，PROJECT.md 这种 50KB+ 文档
            # 会超 asyncio 默认 64KB readline buffer 抛 LimitOverrunError → 直接吞掉后续事件。
            common_kwargs = dict(
                cwd=str(self.project_root),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                limit=10 * 1024 * 1024,
            )
            if use_shell:
                # Windows .cmd shim 走 shell 模式让 cmd.exe 解释。
                # 给所有非纯 ASCII 字母数字/dash/slash 的 arg 强制 "" 包裹，
                # 防 cmd.exe 把 `Write(specs/*)` 里的 () * 当 metachar 展开。
                def _q(a: str) -> str:
                    if not a:
                        return '""'
                    if re.fullmatch(r'[A-Za-z0-9_\-./:=]+', a):
                        return a
                    return '"' + a.replace('"', '""') + '"'
                cmd_str = " ".join(_q(a) for a in cmd)
                proc = await asyncio.create_subprocess_shell(cmd_str, **common_kwargs)
            else:
                proc = await asyncio.create_subprocess_exec(*cmd, **common_kwargs)
            # 暴露 proc 给 interrupt() —— 后者按 client_id 找到 meta，杀这个 proc
            meta["proc"] = proc
        except FileNotFoundError:
            yield AgentError(
                code="claude_cli_missing",
                message=f"`claude` CLI not in PATH (resolved: {claude_bin}, use_shell={use_shell})",
                recoverable=False,
            )
            return

        user_msg = {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        }
        try:
            assert proc.stdin is not None
            proc.stdin.write((json.dumps(user_msg, ensure_ascii=False) + "\n").encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()
        except (BrokenPipeError, ConnectionResetError) as e:
            yield AgentError(code="stdin_closed", message=str(e))
            return

        try:
            assert proc.stdout is not None
            while True:
                try:
                    line = await proc.stdout.readline()
                except (asyncio.LimitOverrunError, ValueError) as e:
                    yield AgentError(code="cc_stream_overflow", message=str(e)[:200])
                    break
                if not line:
                    break
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                t = msg.get("type")
                if t == "system" and msg.get("subtype") == "init":
                    new_sid = msg.get("session_id")
                    if new_sid:
                        meta["cc_session_id"] = new_sid
                        if is_first_turn:
                            yield SessionStarted(client_id=client_id, cc_session_id=new_sid)
                elif t == "assistant":
                    for block in msg.get("message", {}).get("content", []) or []:
                        bt = block.get("type")
                        if bt == "text":
                            yield CcOutputDelta(
                                text=block.get("text", ""),
                                message_id=msg.get("message", {}).get("id"),
                            )
                        elif bt == "thinking":
                            yield CcThinking(text=block.get("thinking", ""))
                        elif bt == "tool_use":
                            yield ToolUseStart(
                                tool=block.get("name", "?"),
                                args=block.get("input", {}),
                                tool_use_id=block.get("id", ""),
                            )
                elif t == "result":
                    if msg.get("is_error"):
                        yield AgentError(
                            code="cc_result_error",
                            message=str(msg.get("result", "unknown"))[:300],
                        )
                    else:
                        yield CcMessageComplete(
                            text=msg.get("result", ""),
                            cost_usd=msg.get("total_cost_usd"),
                            duration_ms=msg.get("duration_ms"),
                            cc_session_id=msg.get("session_id"),
                        )
        finally:
            rc = await proc.wait()
            meta["last_active"] = time.time()
            meta["turn_count"] += 1
            meta.pop("proc", None)  # turn 结束清掉 proc 句柄
            was_interrupted = meta.pop("interrupted", False)
            if was_interrupted:
                # 用户主动 stop —— 不当作 error 报，发 CcInterrupted 让前端显示 "已停止"
                yield CcInterrupted(cc_session_id=meta.get("cc_session_id"))
            elif rc != 0:
                assert proc.stderr is not None
                stderr_bytes = await proc.stderr.read()
                # Windows 上 cc / cmd.exe 的错误信息可能是 cp936（系统 ACP）而非 UTF-8，
                # 直接 utf-8+replace 会把中文报错变成 �，调试时完全看不出问题。
                # 试 utf-8 → cp936（仅 win32）→ replace 兜底。
                stderr_text = ""
                encodings = ("utf-8", "cp936") if sys.platform == "win32" else ("utf-8",)
                for enc in encodings:
                    try:
                        stderr_text = stderr_bytes.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if not stderr_text:
                    stderr_text = stderr_bytes.decode("utf-8", "replace")
                yield AgentError(
                    code="cc_exit_nonzero",
                    message=f"exit={rc} stderr={stderr_text[:200]}",
                )
