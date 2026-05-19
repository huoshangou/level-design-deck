"""Webapp 运行时配置。

副作用：
- 导入即把 PROJECT_ROOT 加到 sys.path（让 backend 任意模块都能 `from tools.* import`）
- 加载 webapp/.env（含 ANTHROPIC_BASE_URL / API_KEY / CUSTOM_HEADERS 等 secret）
"""

from __future__ import annotations
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


_WEBAPP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = _WEBAPP_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# webapp/.env 优先级高于 ~/.claude/.env，不污染用户 cc 配置
load_dotenv(_WEBAPP_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    project_root: Path
    host: str
    port: int
    namespace_default: str
    agent_backend: str           # local | remote
    structured_wizard: bool
    write_tools: bool            # True → Phase 3 完整白名单（Write+Bash），False → Read-only
    remote_gateway_url: str      # DECK_REMOTE_GATEWAY_URL（agent_backend=remote 时必填）
    remote_gateway_token: str | None  # DECK_REMOTE_GATEWAY_TOKEN
    cors_allow_dev_origin: str
    add_dirs: tuple[Path, ...]   # 额外让 cc 能 Read 的目录（--add-dir）
    uploads_dir: Path            # chat 附件临时存放


def _parse_add_dirs(raw: str) -> tuple[Path, ...]:
    out: list[Path] = []
    for s in raw.split(","):
        s = s.strip()
        if not s:
            continue
        p = Path(os.path.expanduser(s)).resolve()
        if p.exists() and p.is_dir():
            out.append(p)
    return tuple(out)


def load_settings() -> Settings:
    return Settings(
        project_root=PROJECT_ROOT,
        host=os.environ.get("DECK_HOST", "127.0.0.1"),
        port=int(os.environ.get("DECK_PORT", "8766")),
        namespace_default=os.environ.get("DECK_NAMESPACE", "default"),
        agent_backend=os.environ.get("DECK_AGENT", "local"),
        structured_wizard=os.environ.get("DECK_STRUCTURED_WIZARD", "0") == "1",
        write_tools=os.environ.get("DECK_WRITE_TOOLS", "1") != "0",
        remote_gateway_url=os.environ.get("DECK_REMOTE_GATEWAY_URL", ""),
        remote_gateway_token=os.environ.get("DECK_REMOTE_GATEWAY_TOKEN") or None,
        cors_allow_dev_origin=os.environ.get("DECK_DEV_ORIGIN", "http://localhost:5173"),
        add_dirs=_parse_add_dirs(os.environ.get("DECK_ADD_DIRS", "~/Desktop")),
        uploads_dir=Path(os.environ.get("DECK_UPLOADS_DIR", str(Path(tempfile.gettempdir()) / "deck-chat-uploads"))),
    )
