"""跨 module 联动校验，wrap tools.cross_check.run_cross_checks。"""

from __future__ import annotations
import contextlib
import io
from typing import Any

from tools.cross_check import collect_specs_by_level, run_cross_checks


def run_cross(level_id: str) -> dict[str, Any]:
    spec_paths = collect_specs_by_level(level_id)
    if not spec_paths:
        return {
            "level_id": level_id,
            "spec_paths": [],
            "modules": [],
            "cross_checks_run": [],
            "errors": [],
            "reviews": [],
            "stats": {"errors": 0, "reviews": 0},
            "warning": f"no spec found for level_id={level_id!r}",
        }
    # run_cross_checks 本体不 print，但子函数 load_spec 等可能；保险起见捕获 stdout
    with contextlib.redirect_stdout(io.StringIO()):
        result, _v = run_cross_checks(spec_paths, level_id)
    return result
