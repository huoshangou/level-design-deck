#!/usr/bin/env python3
"""
render_level.py

按 --level-id 把同 level 所有 module 的 HTML 拼成一份完整关卡文档。
用 iframe 嵌入每个 module 的独立 HTML（避免 CSS 冲突），顶部 sticky 导航。

使用：
  python3 tools/render_level.py --level-id gangster_mansion
  python3 tools/render_level.py --level-id gangster_mansion --render-missing
  → outputs/level_<level_id>__full.html
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 推荐渲染顺序（hub → 空间 → 流程 → 氛围 → 子需求 → 资产）
MODULE_ORDER = [
    "level_overview",
    "spatial_layout",
    "bubble_diagram",
    "atmosphere_ref",
    "lighting_req",
    "vfx_req",
    "audio_req",
    "asset_list",
]

MODULE_LABELS = {
    "level_overview": "关卡概览",
    "spatial_layout": "空间布局",
    "bubble_diagram": "流程图",
    "atmosphere_ref": "氛围参考",
    "lighting_req": "灯光需求",
    "vfx_req": "视觉特效",
    "audio_req": "音频需求",
    "asset_list": "资产清单",
}


def collect_specs_by_level(level_id):
    specs_dir = PROJECT_ROOT / "specs"
    found = []
    for p in sorted(specs_dir.glob("*.spec.json")):
        try:
            spec = json.loads(p.read_text(encoding="utf-8"))
            if spec.get("meta", {}).get("level_id") == level_id:
                sid = spec.get("meta", {}).get("spec_id", p.stem.replace(".spec", ""))
                found.append(sid)
        except Exception:
            continue
    return found


def get_module(spec_id):
    for module in sorted(MODULE_ORDER, key=len, reverse=True):
        if spec_id.startswith(module + "_"):
            return module
    return None


def render_one(spec_id, module):
    spec_path = PROJECT_ROOT / "specs" / f"{spec_id}.spec.json"
    tmpl_path = PROJECT_ROOT / "templates" / f"{module}.html.tmpl"
    out_path = PROJECT_ROOT / "outputs" / f"{spec_id}.html"
    if not spec_path.exists():
        return False, f"spec not found: {spec_path}"
    if not tmpl_path.exists():
        return False, f"template not found: {tmpl_path}"
    r = subprocess.run(
        ["python3", str(PROJECT_ROOT / "tools" / "render.py"), str(spec_path), str(tmpl_path), str(out_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return False, f"render failed: {r.stderr.strip()}"
    return True, str(out_path.relative_to(PROJECT_ROOT))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--level-id", required=True)
    p.add_argument("--output", default=None)
    p.add_argument("--render-missing", action="store_true", help="自动渲染缺失的 module HTML")
    args = p.parse_args()

    spec_ids = collect_specs_by_level(args.level_id)
    if not spec_ids:
        sys.exit(f"ERROR: no spec found for level_id={args.level_id!r}")

    by_module = {}
    for sid in spec_ids:
        m = get_module(sid)
        if m:
            by_module[m] = sid

    ordered = [(m, by_module[m]) for m in MODULE_ORDER if m in by_module]
    if not ordered:
        sys.exit(f"ERROR: no recognized module for level_id={args.level_id!r} (specs={spec_ids})")

    missing = []
    for m, sid in ordered:
        if not (PROJECT_ROOT / "outputs" / f"{sid}.html").exists():
            missing.append((m, sid))

    if missing:
        if args.render_missing:
            print(f"渲染 {len(missing)} 个缺失 module ...")
            for m, sid in missing:
                ok, info = render_one(sid, m)
                print(f"  [{'OK' if ok else 'FAIL'}] {sid}: {info}")
                if not ok:
                    sys.exit(1)
        else:
            print(f"WARN: 缺失渲染：{[sid for _, sid in missing]}")
            print("加 --render-missing 自动补，或手动跑 render.py")
            sys.exit(1)

    nav_links = "\n".join(
        f'  <a href="#{m}" class="nav-link">{MODULE_LABELS[m]}<span class="nav-key">{m}</span></a>'
        for m, _ in ordered
    )
    sections = "\n".join(
        f'  <section id="{m}" class="module-section">\n'
        f'    <h2 class="section-title">{MODULE_LABELS[m]}<span class="section-key">{sid}</span>'
        f'<a href="{sid}.html" class="open-new" target="_blank">独立打开 ↗</a></h2>\n'
        f'    <iframe src="{sid}.html" class="module-frame" title="{MODULE_LABELS[m]}" loading="lazy"></iframe>\n'
        f'  </section>'
        for m, sid in ordered
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{args.level_id} · 完整关卡文档</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,"Helvetica Neue","Noto Sans SC",sans-serif;margin:0;background:#fafaf6;color:#222}}
.top-nav{{position:sticky;top:0;z-index:100;background:#fff;border-bottom:1px solid #ddd;padding:10px 24px;display:flex;gap:4px;flex-wrap:wrap;align-items:center;box-shadow:0 2px 6px rgba(0,0,0,0.04)}}
.top-nav .level-id{{font-weight:600;font-size:13px;color:#1a73e8;padding:4px 10px;margin-right:12px;border-right:1px solid #ddd}}
.top-nav .doc-title{{font-size:12px;color:#666;margin-right:12px}}
.nav-link{{padding:6px 12px;font-size:12px;color:#444;text-decoration:none;border-radius:3px;transition:background .15s}}
.nav-link:hover{{background:#eef4fc;color:#1a73e8}}
.nav-key{{font-family:"JetBrains Mono",monospace;font-size:9px;color:#aaa;margin-left:4px}}
.container{{max-width:1400px;margin:0 auto;padding:20px 24px}}
.module-section{{background:#fff;border:1px solid #e0e0e0;border-radius:4px;margin-bottom:24px;overflow:hidden}}
.section-title{{margin:0;padding:14px 22px;background:#f4f4f0;border-bottom:1px solid #e0e0e0;font-size:15px;font-weight:600;color:#222;display:flex;align-items:center;gap:8px}}
.section-key{{font-family:"JetBrains Mono",monospace;font-size:10px;color:#aaa;font-weight:400;flex:1}}
.open-new{{font-size:11px;color:#1a73e8;text-decoration:none;font-weight:400}}
.open-new:hover{{text-decoration:underline}}
.module-frame{{width:100%;height:780px;border:none;display:block;background:#fff}}
@media print{{
  .top-nav{{position:static}}
  .module-frame{{height:auto;min-height:600px}}
}}
</style>
</head>
<body>
<nav class="top-nav">
  <span class="level-id">{args.level_id}</span>
  <span class="doc-title">完整关卡文档 · {len(ordered)} module</span>
{nav_links}
</nav>
<div class="container">
{sections}
</div>
</body>
</html>
"""

    out = Path(args.output) if args.output else (PROJECT_ROOT / "outputs" / f"level_{args.level_id}__full.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    out_display = out.relative_to(PROJECT_ROOT) if out.is_relative_to(PROJECT_ROOT) else out
    print(f"OK: {len(ordered)} modules → {out_display} ({out.stat().st_size // 1024}KB)")
    print(f"     modules order: {' → '.join(m for m, _ in ordered)}")


if __name__ == "__main__":
    main()
