"""单 module 渲染 + 完整关卡文档渲染。"""

from __future__ import annotations
from typing import Any

from backend.config import PROJECT_ROOT
from backend.store.base import SpecRecord
from tools.render import render
from tools.render_level import (
    build_full_html, render_module_inline, resolve_specs_for_level,
)


def render_spec(spec_record: SpecRecord) -> dict[str, Any]:
    if not spec_record.module:
        raise ValueError(f"cannot infer module for spec_id={spec_record.id!r}")
    tmpl_path = PROJECT_ROOT / "templates" / f"{spec_record.module}.html.tmpl"
    if not tmpl_path.exists():
        raise FileNotFoundError(f"template not found: {tmpl_path}")
    template = tmpl_path.read_text(encoding="utf-8")
    html = render(template, spec_record.content)
    out_path = PROJECT_ROOT / "outputs" / f"{spec_record.id}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {
        "spec_id": spec_record.id,
        "module": spec_record.module,
        "output_path": str(out_path.relative_to(PROJECT_ROOT)),
        "size_bytes": out_path.stat().st_size,
    }


def render_level(level_id: str, render_missing: bool = False) -> dict[str, Any]:
    ordered = resolve_specs_for_level(level_id)
    if not ordered:
        raise ValueError(f"no spec found for level_id={level_id!r}")

    rendered: list[str] = []
    skipped: list[str] = []
    for m, sid in ordered:
        out_path = PROJECT_ROOT / "outputs" / f"{sid}.html"
        if out_path.exists():
            continue
        if not render_missing:
            skipped.append(sid)
            continue
        ok, info = render_module_inline(sid, m)
        if not ok:
            raise RuntimeError(f"render failed for {sid}: {info}")
        rendered.append(sid)

    if skipped:
        raise ValueError(
            f"missing module HTML for {skipped} — set render_missing=True to auto-render"
        )

    html = build_full_html(level_id, ordered)
    out_path = PROJECT_ROOT / "outputs" / f"level_{level_id}__full.html"
    out_path.write_text(html, encoding="utf-8")
    return {
        "level_id": level_id,
        "output_path": str(out_path.relative_to(PROJECT_ROOT)),
        "modules": [m for m, _ in ordered],
        "rendered": rendered,
    }
