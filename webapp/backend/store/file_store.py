"""FileSpecStore：直接读写 ~/Desktop/level-design-deck/specs/*.spec.json。

namespace v1 只支持 'default'；Phase 4 拓展多 namespace 时改 _spec_dir(namespace)
或换成 NamespacedFileStore 子类。
"""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any

from backend.store.base import (
    SaveResult, SpecInfo, SpecInvalid, SpecNotFound, SpecRecord, SpecStore,
)

_SPEC_ID_RE = re.compile(r"^[a-zA-Z0-9_]+$")

# 与 tools/render_level.MODULE_ORDER 同步；放这避免 backend import tools 引入循环风险
_MODULE_PREFIXES = (
    "level_overview", "spatial_layout", "bubble_diagram", "atmosphere_ref",
    "lighting_req", "vfx_req", "audio_req", "asset_list", "demo",
)


def _infer_module(spec_id: str) -> str | None:
    for m in sorted(_MODULE_PREFIXES, key=len, reverse=True):
        if spec_id.startswith(m + "_") or spec_id == m:
            return m
    return None


class FileSpecStore(SpecStore):
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    def _ensure_default_ns(self, namespace: str) -> None:
        if namespace != "default":
            raise NotImplementedError(
                f"namespace={namespace!r} 未实现；Phase 4 拓展"
            )

    def _spec_dir(self, namespace: str) -> Path:
        self._ensure_default_ns(namespace)
        return self.project_root / "specs"

    def _spec_path(self, spec_id: str, namespace: str) -> Path:
        if not _SPEC_ID_RE.match(spec_id):
            raise SpecInvalid(f"spec_id 不合法：{spec_id!r}（仅允许 a-z A-Z 0-9 _）")
        return self._spec_dir(namespace) / f"{spec_id}.spec.json"

    def list(self, namespace: str = "default") -> list[SpecInfo]:
        out: list[SpecInfo] = []
        for p in sorted(self._spec_dir(namespace).glob("*.spec.json")):
            try:
                content = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            meta = content.get("meta", {}) if isinstance(content, dict) else {}
            spec_id = p.stem.removesuffix(".spec")  # 文件名为 canonical ID，与 get() 一致
            out.append(SpecInfo(
                id=spec_id,
                module=_infer_module(spec_id),
                level_id=meta.get("level_id"),
                mtime=p.stat().st_mtime,
            ))
        return out

    def get(self, spec_id: str, namespace: str = "default") -> SpecRecord:
        path = self._spec_path(spec_id, namespace)
        if not path.exists():
            raise SpecNotFound(f"spec 不存在：{spec_id}")
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SpecInvalid(f"spec JSON 解析失败：{e}") from e
        if not isinstance(content, dict):
            raise SpecInvalid(f"spec 顶层不是 object：{type(content).__name__}")
        meta = content.get("meta", {}) or {}
        return SpecRecord(
            id=spec_id,
            content=content,
            mtime=path.stat().st_mtime,
            module=_infer_module(spec_id),
            level_id=meta.get("level_id"),
        )

    def save(self, spec_id: str, content: dict[str, Any], namespace: str = "default") -> SaveResult:
        if not isinstance(content, dict):
            raise SpecInvalid("spec content 必须是 object")
        path = self._spec_path(spec_id, namespace)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return SaveResult(id=spec_id, mtime=path.stat().st_mtime)

    def delete(self, spec_id: str, namespace: str = "default") -> None:
        path = self._spec_path(spec_id, namespace)
        if not path.exists():
            raise SpecNotFound(f"spec 不存在：{spec_id}")
        path.unlink()
