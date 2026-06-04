#!/usr/bin/env python3
"""
infer_cinematography.py — 根据 world_anchor 上下文，生成 LLM prompt 来推断 style_anchor 的摄影字段。

使用方式（与 generate_spec.py 同模式：只产 prompt 不调 LLM）：
  python3 tools/infer_cinematography.py specs/storyboard_xxx.spec.json
  # 把输出的 prompt 贴给 Claude / ChatGPT → 拿回 JSON → 用 Edit 写入 spec

输入：读取 spec 的 world_anchor + context
输出：打印一段结构化 prompt（给 LLM 读），LLM 返回 JSON 填入 style_anchor
"""

import json
import sys
from pathlib import Path

PROMPT_TEMPLATE = """你是一位专业的电影摄影指导（Cinematographer / Director of Photography）。
你需要根据以下游戏关卡/场景的世界设定，推断出最合适的摄影技术参数。

## 世界设定

{world_context}

## 设计意图

{intent}

## 当前 style_anchor（如果已有值，你应该在此基础上优化而非推翻）

{current_style}

## 你需要输出

请以 JSON 格式返回以下字段的建议值（英文，img2img prompt 友好）：

```json
{{
  "lens_and_camera": "摄影设备+镜头。要具体到机型和焦段。例: ARRI Alexa Mini LF, anamorphic 40mm T2.0, shallow depth of field, subtle barrel distortion。选择依据：{era_locale}的影视制作会用什么设备？该场景的氛围需要什么镜头特性（景深/畸变/光晕）？",

  "color_palette": "色彩与影调。要具体到色温、对比度、调色方向。例: teal-orange color grade, crushed blacks below IRE 5, warm tungsten 3200K on skin tones, cool cyan fill, high contrast ratio 4:1。选择依据：该场所的灯光设备会产生什么色温？什么调色风格匹配{era_locale}的影视语言？",

  "lighting_aesthetic": "光感美学。要具体到光源类型与光比。例: motivated practical lighting, warm key from overhead pendant, cool fill from window, strong rim backlight, volumetric haze。选择依据：场所的实际光源（{light_sources}）会产生什么光感？",

  "medium": "画面媒介/渲染风格。例: photorealistic cinematic still, live-action film frame, 35mm motion picture film scan。",

  "art_direction": "艺术方向总纲。例: gritty neo-noir, neon-drenched underworld, naturalistic urban realism。"
}}
```

## 决策原则

1. **设备选择要匹配时代和预算**：{era}的{venue_type}如果被拍成电影/剧集，制作方会用什么设备？独立制片 vs 大制作设备选择不同
2. **镜头选择要匹配情绪**：亲密场景用长焦压缩空间，开阔场景用广角强调环境
3. **色彩要匹配地理文化**：洛杉矶的黑帮题材 vs 东京的黑帮题材，色调完全不同
4. **不要选过于风格化的方案**：除非世界设定明确要求，否则优先选择该题材类型片的主流摄影语言
5. **考虑 AI 生图模型的理解能力**：ARRI / RED / Panavision 等品牌名在训练数据中有强关联，可以用；太小众的器材名 AI 不认识就别用

只输出 JSON，不要其他解释。"""


def build_inference_prompt(spec: dict) -> str:
    world = spec.get("world_anchor", {})
    game_base = world.get("game_base", {})
    context = spec.get("context", {})
    style = spec.get("style_anchor", {})

    world_lines = []
    if game_base:
        for k, v in game_base.items():
            if v:
                world_lines.append(f"- {k}: {v}")
    for k in ("venue_type", "architecture", "material_vocabulary",
              "light_sources", "condition", "atmosphere",
              "population_baseline", "staff_appearance", "protagonist_look",
              "signature_elements"):
        v = world.get(k)
        if v:
            world_lines.append(f"- {k}: {v}")

    style_lines = []
    for k in ("medium", "art_direction", "color_palette",
              "lighting_aesthetic", "lens_and_camera"):
        v = style.get(k)
        if v:
            style_lines.append(f"- {k}: {v}")

    era = game_base.get("era", "contemporary")
    locale = game_base.get("locale", "urban")
    venue_type = world.get("venue_type", "indoor venue")
    light_sources = world.get("light_sources", "mixed lighting")

    return PROMPT_TEMPLATE.format(
        world_context="\n".join(world_lines) or "(未填写)",
        intent=context.get("intent", "(未填写)"),
        current_style="\n".join(style_lines) or "(未填写 — 全部需要你推断)",
        era_locale=f"{era}, {locale}",
        era=era,
        venue_type=venue_type,
        light_sources=light_sources,
    )


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python3 tools/infer_cinematography.py specs/<storyboard>.spec.json")

    spec_path = Path(sys.argv[1])
    if not spec_path.exists():
        sys.exit(f"ERROR: 文件不存在: {spec_path}")

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    prompt = build_inference_prompt(spec)

    print("=" * 70)
    print("以下 prompt 请贴给 LLM（Claude / ChatGPT），拿回 JSON 后填入 spec 的 style_anchor")
    print("=" * 70)
    print()
    print(prompt)
    print()
    print("=" * 70)
    print(f"prompt 长度: {len(prompt)} chars")


if __name__ == "__main__":
    main()
