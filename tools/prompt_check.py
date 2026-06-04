#!/usr/bin/env python3
"""
prompt_check.py — storyboard spec prompt 机械质检。

用 PromptComposer 拼出每个 panel 的 prompt，跑 6 项机械检测，
输出 JSON findings 到 stdout。
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from tools.storyboard_render import PromptComposer, load_spec
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from storyboard_render import PromptComposer, load_spec


SPATIAL_KEYWORDS = re.compile(
    r"\b(left|right|foreground|background|behind|beside|between|"
    r"across|facing|seated|standing|closest|center)\b",
    re.IGNORECASE,
)

GAZE_KEYWORDS = re.compile(
    r"\b(looking|scanning|watching|gazing|staring|eye\s+contact|glances|gaze)\b",
    re.IGNORECASE,
)

CONTRADICTORY_PAIRS = [
    (re.compile(r"\binterior\b", re.I), re.compile(r"\bexterior\b", re.I)),
    (re.compile(r"\bnight\b", re.I), re.compile(r"\bdaytime\b", re.I)),
    (re.compile(r"\bindoor\b", re.I), re.compile(r"\boutdoor\b", re.I)),
]

SECTION_RE = re.compile(r"\[([A-Za-z]+)\]")


def _extract_sections(prompt: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    parts = SECTION_RE.split(prompt)
    i = 1
    while i < len(parts) - 1:
        sections[parts[i]] = parts[i + 1].strip()
        i += 2
    return sections


def _ngrams(text: str, n: int = 3) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def check_panel(
    panel: dict,
    composed: str,
    spec: dict,
    threshold: int,
) -> list[dict]:
    findings: list[dict] = []
    pid = panel.get("panel_id", "?")
    zone_id = (panel.get("zone_id") or "").strip()
    char_ids = panel.get("char_ids") or []
    char_layout = panel.get("char_layout")
    subject_action = panel.get("subject_action") or ""
    camera_position = (panel.get("camera_position") or "").strip()

    scene_anchors = spec.get("scene_anchors") or {}
    world_anchor = spec.get("world_anchor") or {}
    venue_type = (world_anchor.get("venue_type") or "").strip()

    zone_anchor = scene_anchors.get(zone_id) if zone_id else None
    has_scene_prompt = (
        isinstance(zone_anchor, dict)
        and (zone_anchor.get("scene_prompt") or "").strip() != ""
    )

    # C1 VENUE_CONFLICT
    if zone_id and has_scene_prompt and venue_type and venue_type in composed:
        findings.append({
            "panel_id": pid,
            "code": "C1",
            "level": "ERROR",
            "msg": (
                f"venue_type '{venue_type}' still present in composed prompt "
                f"despite zone '{zone_id}' having its own scene_prompt"
            ),
        })

    # C2 SPATIAL_MISSING
    if (
        isinstance(char_ids, list)
        and len(char_ids) >= 2
        and not char_layout
        and not SPATIAL_KEYWORDS.search(subject_action)
    ):
        findings.append({
            "panel_id": pid,
            "code": "C2",
            "level": "REVIEW",
            "msg": (
                f"{len(char_ids)} characters but no char_layout and "
                f"no spatial keywords in subject_action"
            ),
        })

    # C3 GAZE_AMBIGUOUS
    has_orientation = False
    if isinstance(char_layout, list):
        has_orientation = any(
            isinstance(e, dict) and (e.get("orientation") or "").strip()
            for e in char_layout
        )
    if (
        GAZE_KEYWORDS.search(subject_action)
        and not camera_position
        and not has_orientation
    ):
        findings.append({
            "panel_id": pid,
            "code": "C3",
            "level": "REVIEW",
            "msg": "gaze words in subject_action but no camera_position and no char_layout orientation",
        })

    # C4 SCENE_CONFLICT
    sections = _extract_sections(composed)
    scene_text = sections.get("Scene", "")
    for pat_a, pat_b in CONTRADICTORY_PAIRS:
        if pat_a.search(scene_text) and pat_b.search(scene_text):
            findings.append({
                "panel_id": pid,
                "code": "C4",
                "level": "ERROR",
                "msg": (
                    f"contradictory terms in [Scene]: "
                    f"'{pat_a.pattern.strip(chr(92) + 'b')}' vs "
                    f"'{pat_b.pattern.strip(chr(92) + 'b')}'"
                ),
            })

    # C5 PROMPT_TOO_LONG
    if len(composed) > threshold:
        findings.append({
            "panel_id": pid,
            "code": "C5",
            "level": "REVIEW",
            "msg": f"prompt too long: {len(composed)} chars (threshold: {threshold})",
        })

    # C6 DUPLICATE_CONTENT
    if sections:
        seen: Counter[str] = Counter()
        section_of: dict[str, set[str]] = {}
        for sec_name, sec_text in sections.items():
            for ng in _ngrams(sec_text):
                if ng not in section_of:
                    section_of[ng] = set()
                section_of[ng].add(sec_name)
        cross_dupes = 0
        for ng, secs in section_of.items():
            if len(secs) > 1:
                cross_dupes += 1
        if cross_dupes > 5:
            findings.append({
                "panel_id": pid,
                "code": "C6",
                "level": "REVIEW",
                "msg": f"{cross_dupes} 3-word n-grams duplicated across different sections",
            })

    return findings


def run_checks(spec_path: Path, threshold: int) -> dict:
    spec = load_spec(spec_path)
    composer = PromptComposer(spec)
    panels = spec.get("panels", [])

    all_findings: list[dict] = []
    panel_count = 0

    for panel in panels:
        if not isinstance(panel, dict):
            continue
        panel_count += 1
        composed = composer.compose(panel, sanitize=False)
        findings = check_panel(panel, composed, spec, threshold)
        all_findings.extend(findings)

    errors = sum(1 for f in all_findings if f["level"] == "ERROR")
    reviews = sum(1 for f in all_findings if f["level"] == "REVIEW")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec_path": str(spec_path),
        "findings": all_findings,
        "stats": {
            "panels": panel_count,
            "findings": len(all_findings),
            "errors": errors,
            "reviews": reviews,
        },
    }


def main():
    ap = argparse.ArgumentParser(
        description="Mechanical quality checks on storyboard spec prompts."
    )
    ap.add_argument("spec_path", type=Path, help="path to storyboard spec JSON")
    ap.add_argument(
        "--threshold",
        type=int,
        default=1500,
        help="max prompt chars before C5 fires (default: 1500)",
    )
    args = ap.parse_args()
    if not args.spec_path.exists():
        sys.exit(f"ERROR: spec not found: {args.spec_path}")

    result = run_checks(args.spec_path, args.threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["stats"]["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
