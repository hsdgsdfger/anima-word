# -*- coding: utf-8 -*-
"""负面提示词：按正向标签推导，而不是写死一串。

参考 PromptForge 的思路（仅借鉴功能设计，不复制其数据）：
  · 标准版 = 模型基线 + 通用质量项 + 冲突互斥 + 档位压制
  · 全量版 = 再补画质 / 噪点 / 文字 / 构图 / 光影
  · 与正向重复的词自动跳过
  · 正向要 NSFW 时，自动剔除压制词（nsfw / censored / safe 等）
"""
from __future__ import annotations

import re

BASE = [
    "lowres", "bad anatomy", "bad hands", "text", "error", "missing finger",
    "extra digit", "fewer digits", "cropped", "worst quality", "low quality",
    "normal quality", "jpeg artifacts", "signature", "watermark", "username",
    "blurry", "artist name", "bad proportions", "malformed limbs",
    "extra limbs", "disconnected limbs", "fused fingers", "extra fingers",
]

FULL_EXTRA = [
    "ugly", "duplicate", "mutation", "deformed", "disfigured", "out of frame",
    "bad feet", "bad ears", "bad face", "long neck", "missing arms",
    "missing legs", "extra arms", "extra legs", "more than two legs",
    "more than two arms", "poorly drawn face", "poorly drawn hands",
    "poorly drawn feet", "mutation", "noise", "grain", "chromatic aberration",
    "oversaturated", "overexposed", "underexposed", "motion blur",
    "compression artifacts", "text logo", "watermark", "signature",
    "english text", "chinese text", "japanese text", "speech bubble",
    "border", "frame", "collage", "multiple views", "reference sheet",
]

# 只加到 0 档：让低档更干净。高档不能加，否则会把要露的内容压回去。
SFW_SUPPRESS = ["nsfw", "explicit", "nude", "nipples", "pussy", "penis",
                "sex", "cum", "censored"]

# 正向出现这些词时，负面里对应项要剔除（否则自相矛盾）。
POSITIVE_ECHO = {
    "nsfw": {"nsfw", "explicit", "censored", "safe"},
    "explicit": {"nsfw", "explicit", "censored", "safe"},
    "nude": {"nude", "nsfw", "censored"},
    "completely nude": {"nude", "nsfw", "censored"},
    "censored": {"censored", "uncensored"},
    "uncensored": {"censored"},
    "monochrome": {"monochrome", "greyscale"},
    "greyscale": {"monochrome", "greyscale"},
    "mosaic censoring": {"censored", "mosaic censoring"},
}

# 冲突对：正向有 A，负面加 B。只在 B 还没被正向使用时才加。
CONFLICT_PAIRS = [
    ("day", "night"),
    ("night", "day"),
    ("outdoors", "indoors"),
    ("indoors", "outdoors"),
    ("long hair", "short hair"),
    ("short hair", "long hair"),
    ("smile", "crying"),
    ("crying", "smile"),
    ("standing", "lying"),
    ("lying", "standing"),
    ("from above", "from below"),
    ("from below", "from above"),
    ("looking at viewer", "looking away"),
    ("looking away", "looking at viewer"),
    ("solo", "multiple girls"),
    ("1girl, solo", "multiple girls"),
    ("2girls", "solo"),
    ("1boy", "multiple boys"),
    ("full body", "cowboy shot"),
    ("cowboy shot", "full body"),
    ("close-up", "full body"),
    ("open mouth", "closed mouth"),
    ("closed mouth", "open mouth"),
]

TEXTURE_NEG = ["blurry", "out of focus", "depth of field", "bokeh"]

_PUNCT = re.compile(r"[\s_]+")
_WEIGHT_WRAP = re.compile(r"^\(+([^():]+?)(?::\s*[0-9.]+\s*)?\)+$")


def _split(text):
    return [t.strip().lower() for t in str(text or "").replace("\n", ",").split(",")
            if t.strip()]


def _norm(t):
    return _PUNCT.sub(" ", str(t or "").strip().lower())


def _base_tag(t):
    """把 `(night:1.2)` / `((night))` 还原成 `night`，供冲突、回声和去重匹配。

    输出正文仍保留原始权重语法；这里只生成匹配用的基础标签。
    """
    s = _norm(t)
    m = _WEIGHT_WRAP.match(s)
    if m:
        s = _norm(m.group(1))
    return s


def _has_any(tags, needles):
    return any(n in tags for n in needles)


def build_negative(positive="", level=0, preset="standard", extra=""):
    """返回负面提示词字符串。

    level 用 0-4 的整数（与 V6 档位同口径）；字符串 "sfw"/"explicit" 也认。
    preset: "none" / "standard" / "full"
    """
    if str(preset or "").strip().lower() == "none":
        return str(extra or "").strip()

    lv = level
    if isinstance(level, str):
        lv = {"sfw": 0, "suggestive": 1, "explicit": 2,
              "hardcore": 3, "extreme": 4}.get(level.strip().lower(), 0)
    lv = int(lv or 0)

    pos_tags = {_base_tag(t) for t in _split(positive)}
    tags = [t for t in BASE]
    if str(preset or "").strip().lower() == "full":
        tags.extend(FULL_EXTRA)

    if lv == 0:
        tags.extend(SFW_SUPPRESS)

    for key, drop in POSITIVE_ECHO.items():
        if _has_any(pos_tags, {key}) or key in pos_tags:
            tags = [t for t in tags if t not in drop]

    for a, b in CONFLICT_PAIRS:
        if a in pos_tags and b not in pos_tags:
            tags.append(b)

    # 去重保序 + 跳过与正向重复的词
    out, seen = [], set()
    for t in tags:
        t = _norm(t)
        if not t or t in seen or t in pos_tags:
            continue
        seen.add(t)
        out.append(t)

    for t in _split(extra):
        t = _norm(t)
        if t and t not in seen and t not in pos_tags:
            seen.add(t)
            out.append(t)
    return ", ".join(out)
