"""build prompt 文本给 chat / wizard。

v1 只产 prompt 不调 LLM（与 tools/generate_spec.py 一致原则）；
Phase 2 chat 会把 prompt 作为指令传给 cc 子进程。
"""

from __future__ import annotations
from pathlib import Path

from backend.config import PROJECT_ROOT
from tools.generate_spec import MODULES, build_prompt as _build_module_prompt
from tools.regenerate_field import build_prompt as _build_field_prompt


def list_modules() -> list[dict]:
    out = []
    for name, cfg in MODULES.items():
        out.append({
            "name": name,
            "schema_path": cfg.get("schema_path"),
            "demo_path": cfg.get("demo_path"),
            "lvm_generated": cfg.get("lvm_generated", True),
            "spec_id_pattern": cfg.get("spec_id_pattern"),
        })
    return out


def build_module_prompt(module: str, intent: str) -> str:
    if module not in MODULES:
        raise ValueError(f"unknown module={module!r}; available={list(MODULES)}")
    if not MODULES[module].get("lvm_generated", True):
        raise ValueError(f"module={module!r} 不支持 LLM 生成（数据源是外部工具）")
    return _build_module_prompt(module, intent)


def build_field_prompt(spec_id: str, field_path: str, hint: str = "") -> str:
    spec_path = PROJECT_ROOT / "specs" / f"{spec_id}.spec.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"spec not found: {spec_path}")

    schema_dir = PROJECT_ROOT / "schema"
    candidates = sorted(
        (p.name[:-len(".schema.json")] for p in schema_dir.glob("*.schema.json")),
        key=len, reverse=True,
    )
    schema_path: Path | None = None
    for m in candidates:
        if m in spec_id:
            schema_path = schema_dir / f"{m}.schema.json"
            module = m
            break
    if not schema_path or not schema_path.exists():
        raise ValueError(f"cannot infer schema for spec_id={spec_id!r}")

    if not MODULES.get(module, {}).get("lvm_generated", True):
        raise ValueError(f"module={module!r} 不支持字段重生成（数据源是外部工具）")

    return _build_field_prompt(spec_path, schema_path, field_path, hint)
