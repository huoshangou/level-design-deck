#!/usr/bin/env python3
"""
storyboard_render.py — 给 storyboard spec 拼接 img2img prompt，原子写回。

设计要点：
- prompt_template 中 {style.<field>} 取自 style_anchor；{<field>} 取自 panel。
- 空字段继承规则：panel.lighting 留空 → 用 style_anchor.lighting_aesthetic；
  panel.source_image_url 留空 → 用 style_anchor.reference_image_url。
- quality_tags 是 array → join(", ")。
- ImageProvider ABC 预留：当前 DummyProvider only，未来加 Image2Provider / SDProvider 子类。
- spec 不变结构，仅回填 panels[].generated_prompt / generated_image_url / generation_meta。

使用：
  python3 tools/storyboard_render.py specs/storyboard_X.spec.json --prompt-only
  python3 tools/storyboard_render.py specs/storyboard_X.spec.json --provider dummy
  python3 tools/storyboard_render.py specs/storyboard_X.spec.json --provider image2 --api-key $KEY  # 未来
"""

import argparse
import json
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Prompt composer
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATE = (
    "{style.medium}, {style.art_direction}, "
    "{scene}, {subject_action}, {camera}, {lighting}, {mood}, "
    "{style.color_palette}, {style.quality_tags}"
)

# 空字段继承表：panel field → style_anchor field
INHERIT_MAP = {
    "lighting": "lighting_aesthetic",
}

PLACEHOLDER_RE = re.compile(r"\{(style\.)?([a-zA-Z_][a-zA-Z0-9_]*)\}")


class PromptComposer:
    def __init__(self, spec: dict):
        self.style = spec.get("style_anchor", {})
        self.template = spec.get("prompt_template") or DEFAULT_TEMPLATE

    def _style_value(self, field: str) -> str:
        v = self.style.get(field)
        if v is None:
            return ""
        if isinstance(v, list):
            return ", ".join(str(x) for x in v if x)
        return str(v).strip()

    def _panel_value(self, panel: dict, field: str) -> str:
        v = panel.get(field, "")
        if v is None:
            v = ""
        v = str(v).strip()
        # 空字段继承
        if not v and field in INHERIT_MAP:
            v = self._style_value(INHERIT_MAP[field])
        return v

    def _resolve(self, panel: dict, match) -> str:
        is_style = match.group(1) == "style."
        field = match.group(2)
        if is_style:
            return self._style_value(field)
        return self._panel_value(panel, field)

    def compose(self, panel: dict) -> str:
        raw = PLACEHOLDER_RE.sub(lambda m: self._resolve(panel, m), self.template)
        # 清理：去掉 ", , " / 多空格 / 首尾标点
        cleaned = re.sub(r",\s*,", ",", raw)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r",\s*$", "", cleaned).strip(" ,")
        return cleaned

    def resolved_source_image(self, panel: dict) -> str:
        url = (panel.get("source_image_url") or "").strip()
        if not url:
            url = (self.style.get("reference_image_url") or "").strip()
        return url


# ---------------------------------------------------------------------------
# Image provider abstraction (API 预留)
# ---------------------------------------------------------------------------

class ImageProvider(ABC):
    name = "abstract"

    @abstractmethod
    def generate(self, prompt: str, source_image_url: str, negative_prompt: str = "",
                 strength: float = 0.6, **kw) -> dict:
        """返回 {generated_image_url: str, generation_meta: dict}"""


class DummyProvider(ImageProvider):
    name = "dummy"

    def generate(self, prompt, source_image_url, negative_prompt="", strength=0.6, **kw):
        return {
            "generated_image_url": "",
            "generation_meta": {
                "provider": self.name,
                "prompt_chars": len(prompt),
                "source": source_image_url or "(none)",
                "note": "no API call performed",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        }


def make_provider(name: str, api_key: str = "") -> ImageProvider:
    if name in ("dummy", "prompt-only", "none"):
        return DummyProvider()
    raise SystemExit(
        f"ERROR: provider {name!r} not implemented yet. "
        f"Available: dummy. Future candidates: image2, sd, midjourney, flux."
    )


# ---------------------------------------------------------------------------
# Spec I/O
# ---------------------------------------------------------------------------

def load_spec(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"ERROR: cannot load spec {path}: {e}")


def is_storyboard_spec(spec: dict) -> bool:
    sid = spec.get("meta", {}).get("spec_id", "")
    return sid.startswith("storyboard_")


def atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def render_storyboard(spec_path: Path, provider_name: str,
                       api_key: str = "", strength: float = 0.6,
                       prompt_only: bool = False, dry_run: bool = False) -> dict:
    spec = load_spec(spec_path)
    if not is_storyboard_spec(spec):
        sys.exit(f"ERROR: {spec_path} is not a storyboard spec (meta.spec_id must start with 'storyboard_').")

    composer = PromptComposer(spec)
    provider = None if prompt_only else make_provider(provider_name, api_key)
    style_neg = (spec.get("style_anchor", {}).get("negative_prompt") or "").strip()

    panels = spec.get("panels", [])
    stats = {"total": len(panels), "prompts_composed": 0, "images_generated": 0}

    for panel in panels:
        if not isinstance(panel, dict):
            continue
        prompt = composer.compose(panel)
        panel["generated_prompt"] = prompt
        stats["prompts_composed"] += 1

        if provider is not None:
            src = composer.resolved_source_image(panel)
            result = provider.generate(
                prompt=prompt,
                source_image_url=src,
                negative_prompt=style_neg,
                strength=strength,
            )
            panel["generated_image_url"] = result.get("generated_image_url", "")
            panel["generation_meta"] = result.get("generation_meta", {})
            if panel["generated_image_url"]:
                stats["images_generated"] += 1

    if not dry_run:
        atomic_write(spec_path, spec)
    return stats


def main():
    ap = argparse.ArgumentParser(description="Compose img2img prompts for a storyboard spec.")
    ap.add_argument("spec_path", type=Path, help="storyboard spec JSON file path")
    ap.add_argument("--prompt-only", action="store_true",
                    help="Only compose generated_prompt, do not call any provider")
    ap.add_argument("--provider", default="dummy",
                    help="Image provider: dummy (default). Future: image2 / sd / midjourney / flux.")
    ap.add_argument("--api-key", default="", help="Provider API key (when needed)")
    ap.add_argument("--strength", type=float, default=0.6, help="img2img denoise strength")
    ap.add_argument("--dry-run", action="store_true", help="Do not write the spec back")
    args = ap.parse_args()

    if not args.spec_path.exists():
        sys.exit(f"ERROR: spec not found: {args.spec_path}")

    stats = render_storyboard(
        spec_path=args.spec_path,
        provider_name=args.provider,
        api_key=args.api_key,
        strength=args.strength,
        prompt_only=args.prompt_only,
        dry_run=args.dry_run,
    )

    mode = "prompt-only" if args.prompt_only else f"provider={args.provider}"
    suffix = " (DRY RUN, not written)" if args.dry_run else ""
    print(f"OK [{mode}]: {args.spec_path}")
    print(f"  panels={stats['total']} prompts_composed={stats['prompts_composed']} "
          f"images_generated={stats['images_generated']}{suffix}")


if __name__ == "__main__":
    main()
