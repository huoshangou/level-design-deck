#!/usr/bin/env python3
"""
storyboard_render.py — storyboard spec → img2img prompt 拼接 + 原子写回。

v0.8: venue_type 条件注入 / char_layout 分段式 Subject / camera_position /
      negative_additions / markdown 格式输出。
"""

import argparse
import json
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TEMPLATE = (
    "[Style] {style.medium}, {style.art_direction}, {style.lens_and_camera}.\n\n"
    "[Color] {style.color_palette}.\n\n"
    "[Shot] {shot_size}, {composition}, {camera_technique}.\n\n"
    "[Scene] {scene}.\n\n"
    "[Subject]\n{subject_action}\n\n"
    "[Lighting] {lighting}.\n\n"
    "[Mood] {mood}.\n\n"
    "[Quality] {style.quality_tags}"
)

INHERIT_MAP = {"lighting": "lighting_aesthetic"}
PLACEHOLDER_RE = re.compile(r"\{(style\.|world\.)?([a-zA-Z_][a-zA-Z0-9_]*)\}")
GAME_BASE_FIELDS = ("era", "locale", "tech_level", "cultural_context")


def _build_game_prefix(world: dict) -> str:
    game = world.get("game_base", {})
    return ", ".join(
        v for f in GAME_BASE_FIELDS if (v := (game.get(f) or "").strip())
    )


class PromptComposer:
    def __init__(self, spec: dict):
        self.style = spec.get("style_anchor", {})
        self.world = spec.get("world_anchor", {})
        self.template = spec.get("prompt_template") or DEFAULT_TEMPLATE
        self.game_prefix = _build_game_prefix(self.world)
        self.venue_type = (self.world.get("venue_type") or "").strip()
        self._scene_anchor_images: dict[str, str] = {}
        self._scene_prompts: dict[str, str] = {}
        for zone_id, anchor in (spec.get("scene_anchors") or {}).items():
            if not isinstance(anchor, dict):
                continue
            sp = (anchor.get("scene_prompt") or "").strip()
            if sp:
                self._scene_prompts[zone_id] = sp
            if anchor.get("approved") and anchor.get("image_url"):
                self._scene_anchor_images[zone_id] = anchor["image_url"]
        self._char_map: dict[str, str] = {}
        for c in spec.get("characters", []):
            if isinstance(c, dict) and c.get("char_id") and c.get("appearance"):
                self._char_map[c["char_id"]] = c["appearance"].strip()

    def _style_value(self, field: str) -> str:
        v = self.style.get(field)
        if v is None:
            return ""
        if isinstance(v, list):
            return ", ".join(str(x) for x in v if x)
        return str(v).strip()

    def _world_value(self, field: str) -> str:
        v = self.world.get(field)
        if v is None:
            v = self.world.get("game_base", {}).get(field)
        if v is None:
            return ""
        if isinstance(v, list):
            return ", ".join(str(x) for x in v if x)
        return str(v).strip()

    def _panel_value(self, panel: dict, field: str) -> str:
        v = str(panel.get(field, "") or "").strip()
        if not v and field == "shot_size":
            v = (panel.get("camera") or "").strip()
        if not v and field in INHERIT_MAP:
            v = self._style_value(INHERIT_MAP[field])
        if field == "camera_technique":
            cam_pos = (panel.get("camera_position") or "").strip()
            if cam_pos:
                v = f"{v}\n{cam_pos}" if v else cam_pos
        return v

    def _resolve(self, panel: dict, match) -> str:
        prefix = match.group(1) or ""
        field = match.group(2)
        if prefix == "style.":
            return self._style_value(field)
        if prefix == "world.":
            return self._world_value(field)
        return self._panel_value(panel, field)

    def _build_structured_subject(self, panel: dict) -> str:
        char_layout = panel.get("char_layout")
        if not char_layout or not isinstance(char_layout, list):
            return ""
        parts: list[str] = []
        for entry in char_layout:
            if not isinstance(entry, dict):
                continue
            cid = entry.get("char_id", "")
            appearance = self._char_map.get(cid, "")
            pos = entry.get("position", "")
            orient = entry.get("orientation", "")
            action = entry.get("action", "")
            header = ", ".join(filter(None, [pos, orient]))
            body_parts = [x for x in [appearance, action] if x]
            body = ", ".join(body_parts)
            if header:
                parts.append(f"{header}:\n{body}")
            else:
                parts.append(body)
        return "\n\n".join(parts)

    def compose(self, panel: dict, sanitize: bool = True) -> str:
        panel = dict(panel)
        has_world_ph = "{world." in self.template
        zone_id = (panel.get("zone_id") or "").strip()
        has_scene_prompt = zone_id and zone_id in self._scene_prompts

        scene_parts: list[str] = []
        if not has_world_ph:
            if self.game_prefix:
                scene_parts.append(self.game_prefix)
            if self.venue_type and not has_scene_prompt:
                scene_parts.append(self.venue_type)
        if has_scene_prompt:
            scene_parts.append(self._scene_prompts[zone_id])
        panel_scene = (panel.get("scene") or "").strip()
        if panel_scene:
            scene_parts.append(panel_scene)
        panel["scene"] = ", ".join(scene_parts) if scene_parts else ""

        structured = self._build_structured_subject(panel)
        if structured:
            panel["subject_action"] = structured
        else:
            char_ids = panel.get("char_ids", [])
            if char_ids and isinstance(char_ids, list):
                appearances = [self._char_map[c] for c in char_ids if c in self._char_map]
                if appearances:
                    sa = (panel.get("subject_action") or "").strip()
                    prefix = ", ".join(appearances)
                    panel["subject_action"] = f"{prefix}, {sa}" if sa else prefix

        raw = PLACEHOLDER_RE.sub(lambda m: self._resolve(panel, m), self.template)
        cleaned = re.sub(r"\[[A-Za-z]+\]\s*[.,]\s*(?=\[|$)", "", raw)
        cleaned = re.sub(r",\s*[.,]", ",", cleaned)
        cleaned = re.sub(r",\s*,", ",", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = cleaned.strip(" ,.")
        if sanitize:
            try:
                from tools.prompt_sanitizer import sanitize_prompt
            except ModuleNotFoundError:
                from prompt_sanitizer import sanitize_prompt
            cleaned = sanitize_prompt(cleaned)
        return cleaned

    def resolved_source_image(self, panel: dict) -> str:
        url = (panel.get("source_image_url") or "").strip()
        if not url:
            zid = (panel.get("zone_id") or "").strip()
            if zid and zid in self._scene_anchor_images:
                url = self._scene_anchor_images[zid]
        if not url:
            url = (self.style.get("reference_image_url") or "").strip()
        return url

    def scene_anchor_for(self, panel: dict) -> str:
        zid = (panel.get("zone_id") or "").strip()
        return self._scene_anchor_images.get(zid, "")

    def negative_prompt(self, panel: dict) -> str:
        base = (self.style.get("negative_prompt") or "").strip()
        adds = (panel.get("negative_additions") or "").strip()
        if base and adds:
            return f"{base}, {adds}"
        return base or adds


# --- Image provider abstraction ---

class ImageProvider(ABC):
    name = "abstract"
    @abstractmethod
    def generate(self, prompt: str, source_image_url: str,
                 negative_prompt: str = "", strength: float = 0.6, **kw) -> dict: ...


class DummyProvider(ImageProvider):
    name = "dummy"
    def generate(self, prompt, source_image_url, negative_prompt="", strength=0.6, **kw):
        return {
            "generated_image_url": "",
            "generation_meta": {
                "provider": self.name, "prompt_chars": len(prompt),
                "source": source_image_url or "(none)", "note": "no API call",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        }


def make_provider(name: str, api_key: str = "") -> ImageProvider:
    if name in ("dummy", "prompt-only", "none"):
        return DummyProvider()
    sys.exit(f"ERROR: provider {name!r} not implemented. Available: dummy.")


# --- Spec I/O ---

def load_spec(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"ERROR: cannot load spec {path}: {e}")


def atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


# --- Main ---

def render_storyboard(spec_path: Path, provider_name: str,
                      api_key: str = "", strength: float = 0.6,
                      prompt_only: bool = False, dry_run: bool = False) -> dict:
    spec = load_spec(spec_path)
    sid = spec.get("meta", {}).get("spec_id", "")
    if not sid.startswith("storyboard_"):
        sys.exit(f"ERROR: {spec_path} is not a storyboard spec.")
    composer = PromptComposer(spec)
    provider = None if prompt_only else make_provider(provider_name, api_key)
    panels = spec.get("panels", [])
    stats = {"total": len(panels), "prompts_composed": 0, "images_generated": 0}
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        prompt = composer.compose(panel)
        panel["generated_prompt"] = prompt
        stats["prompts_composed"] += 1
        if provider is not None:
            neg = composer.negative_prompt(panel)
            src = composer.resolved_source_image(panel)
            result = provider.generate(prompt=prompt, source_image_url=src,
                                       negative_prompt=neg, strength=strength)
            panel["generated_image_url"] = result.get("generated_image_url", "")
            panel["generation_meta"] = result.get("generation_meta", {})
            if panel["generated_image_url"]:
                stats["images_generated"] += 1
    if not dry_run:
        atomic_write(spec_path, spec)
    return stats


def main():
    ap = argparse.ArgumentParser(description="Compose img2img prompts for storyboard spec.")
    ap.add_argument("spec_path", type=Path)
    ap.add_argument("--prompt-only", action="store_true")
    ap.add_argument("--provider", default="dummy")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--strength", type=float, default=0.6)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.spec_path.exists():
        sys.exit(f"ERROR: spec not found: {args.spec_path}")
    stats = render_storyboard(args.spec_path, args.provider, args.api_key,
                              args.strength, args.prompt_only, args.dry_run)
    mode = "prompt-only" if args.prompt_only else f"provider={args.provider}"
    sfx = " (DRY RUN)" if args.dry_run else ""
    print(f"OK [{mode}]: {args.spec_path}{sfx}")
    print(f"  panels={stats['total']} prompts={stats['prompts_composed']} "
          f"images={stats['images_generated']}")


if __name__ == "__main__":
    main()
