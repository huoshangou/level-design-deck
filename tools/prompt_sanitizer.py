#!/usr/bin/env python3
"""
prompt_sanitizer.py — 导出 prompt 时的脱敏后处理。

设计原则：
- spec 里保持真实描述，脱敏只作用于导出的 prompt 文本
- 用电影工业专业语言重述同一画面，不改变视觉意图
- 规则按长度降序匹配（长词组优先于单词，防止部分替换）
- 可叠加：先跑词组替换，再跑单词替换，最后跑结构规则
"""

import re

# ── 词组替换（长 → 短排序，优先匹配） ──

_PHRASE_RULES: list[tuple[str, str]] = [
    # venue / location
    ("strip club", "neon-lit cabaret lounge"),
    ("strip bar", "nightclub lounge"),
    ("strip joint", "underground nightclub"),
    ("red light district", "nocturnal entertainment district"),
    ("red-light district", "nocturnal entertainment district"),
    ("sex shop", "adult retail storefront"),
    ("brothel", "underground establishment"),
    ("massage parlor", "private wellness parlor"),
    # people
    ("exotic dancer", "cabaret entertainer"),
    ("pole dancer", "aerial performer"),
    ("pole dancing", "aerial performance"),
    ("lap dance", "private performance"),
    ("go-go dancer", "club performer"),
    ("female dancer", "performer"),
    ("male dancer", "performer"),
    ("stripper", "stage performer"),
    ("stripping", "performing on stage"),
    ("call girl", "underworld contact"),
    ("prostitute", "underworld figure"),
    ("prostitution", "illicit trade"),
    # appearance
    ("scantily clad", "in stage costume"),
    ("scantily dressed", "in performance attire"),
    ("barely dressed", "in minimal stage attire"),
    ("revealing outfit", "form-fitting stage costume"),
    ("revealing clothing", "performance wardrobe"),
    ("see-through", "sheer-fabric"),
    ("topless", "backlit silhouette"),
    ("half-naked", "partially silhouetted"),
    # substances
    ("drug deal", "contraband exchange"),
    ("drug dealer", "contraband supplier"),
    ("drug den", "underground den"),
    ("crack pipe", "glass pipe"),
    ("snorting cocaine", "hunched over table"),
    ("cocaine", "illicit powder"),
    ("heroin", "contraband"),
    ("methamphetamine", "contraband"),
    ("injecting drugs", "in a compromised state"),
    # violence (selective — keep cinematic combat, sanitize graphic)
    ("pool of blood", "dark liquid pooling on floor"),
    ("blood-soaked", "stain-covered"),
    ("blood splatter", "dark splatter marks"),
    ("severed", "damaged"),
    ("mutilated", "ravaged"),
    ("corpse", "motionless figure"),
    ("dead body", "fallen figure"),
]

# ── 单词替换（情绪/形容词级别） ──

_WORD_RULES: list[tuple[str, str]] = [
    ("seductive", "captivating"),
    ("sensual", "graceful"),
    ("provocative", "striking"),
    ("erotic", "atmospheric"),
    ("sultry", "smoky"),
    ("voluptuous", "statuesque"),
    ("intoxicating allure", "commanding presence"),
    ("allure", "presence"),
    ("lust", "tension"),
    ("arousing", "compelling"),
    ("naked", "unclothed silhouette"),
    ("nude", "figure study"),
    ("nudity", "exposed form"),
    ("lingerie", "performance attire"),
    ("underwear", "stage costume"),
    ("cleavage", "neckline"),
    ("busty", "striking figure"),
]

# ── 结构规则（正则） ──

_REGEX_RULES: list[tuple[re.Pattern, str]] = [
    # "female/woman ... dancing" 拆性别标注
    (re.compile(r"\b(female|woman|girl)\s+(dancer|stripper|performer)", re.I),
     r"performer"),
    # "sexy [noun]" → "stylish [noun]"
    (re.compile(r"\bsexy\s+", re.I), "stylish "),
    # "hot [person-noun]" → "[person-noun]"（保留 "hot pink" 等色彩词）
    (re.compile(r"\bhot\s+(woman|girl|dancer|performer|model)\b", re.I),
     r"striking \1"),
]


def sanitize_prompt(text: str) -> str:
    for old, new in _PHRASE_RULES:
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    for old, new in _WORD_RULES:
        text = re.sub(r"\b" + re.escape(old) + r"\b", new, text, flags=re.IGNORECASE)
    for pattern, repl in _REGEX_RULES:
        text = pattern.sub(repl, text)
    # 清理多余空格/逗号
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
