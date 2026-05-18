"""集成 mechanical_check + template_diff 给单个 spec 跑全检。"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT
from backend.store.base import SpecRecord
from tools.mechanical_check import Validator, infer_module, SEMANTIC_CHECKS
from tools.template_diff import build_diff_payload


def _infer_schema_path(spec_id: str) -> Path | None:
    schema_dir = PROJECT_ROOT / "schema"
    candidates = sorted(
        (p.name[:-len(".schema.json")] for p in schema_dir.glob("*.schema.json")),
        key=len, reverse=True,
    )
    for module in candidates:
        if module in spec_id:
            return schema_dir / f"{module}.schema.json"
    return None


def run_check(spec_record: SpecRecord) -> dict[str, Any]:
    schema_path = _infer_schema_path(spec_record.id)
    if not schema_path or not schema_path.exists():
        return {
            "mechanical": {
                "errors": [{
                    "level": "ERROR", "field_path": "<meta>", "rule": "no_schema",
                    "msg": f"cannot infer schema for spec_id={spec_record.id!r}",
                }],
                "reviews": [],
                "stats": {"errors": 1, "reviews": 0},
            },
            "template": None,
        }

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    v = Validator(schema)
    v.check(spec_record.content)
    module = infer_module(spec_record.content, schema)
    if module and module in SEMANTIC_CHECKS:
        SEMANTIC_CHECKS[module](spec_record.content, v)

    template_payload = None
    work_docs_path = PROJECT_ROOT / "reference" / "work_docs_extract.json"
    tmpl_fields_path = PROJECT_ROOT / "reference" / "template_fields.json"
    if work_docs_path.exists() and tmpl_fields_path.exists():
        work_docs = json.loads(work_docs_path.read_text(encoding="utf-8"))
        tmpl_fields = json.loads(tmpl_fields_path.read_text(encoding="utf-8"))
        template_payload = build_diff_payload(
            spec_record.content, work_docs, tmpl_fields,
            spec_path_str=str(PROJECT_ROOT / "specs" / f"{spec_record.id}.spec.json"),
        )

    return {
        "mechanical": {
            "errors": v.errors,
            "reviews": v.reviews,
            "stats": {"errors": len(v.errors), "reviews": len(v.reviews)},
            "module": module,
            "schema_path": str(schema_path.relative_to(PROJECT_ROOT)),
        },
        "template": template_payload,
    }
