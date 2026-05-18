"""Deck 视图渲染，wrap tools.render_deck.render_deck。"""

from __future__ import annotations
import contextlib
import io
from typing import Any

from backend.config import PROJECT_ROOT
from tools.render_deck import render_deck as _render_deck_html


def render_deck(level_id: str) -> dict[str, Any]:
    # render_deck 内部对缺失 module 会 print 到 stderr，捕获掉避免污染日志
    with contextlib.redirect_stderr(io.StringIO()):
        html = _render_deck_html(level_id)
    out_path = PROJECT_ROOT / "outputs" / f"level_{level_id}__deck.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {
        "level_id": level_id,
        "output_path": str(out_path.relative_to(PROJECT_ROOT)),
        "size_bytes": out_path.stat().st_size,
    }
