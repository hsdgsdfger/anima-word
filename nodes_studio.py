# -*- coding: utf-8 -*-
"""新插件的节点：主工坊节点 + CLIP 编码 + 多提示词框 + 通用选择器。

设计原则：
  · 主节点继承 V6 的 `AnimaV4RandomPrompt`，控件顺序**只在末尾追加**，
    V6 面板因此可以原样复用（它按控件名读写，不按序号）。
  · `studio_json` 是手选状态的唯一真源；面板写、节点读。
  · 所有新增输出都追加在 V6 的 4 个输出之后，不破坏老连线。
"""
from __future__ import annotations

import json
import random
import zlib
import itertools
import time

try:
    from . import anima_v4_pngmeta as PM
    from . import anima_v4_rules as R
    from . import catalog
    from . import manual
    from . import nodes_v6 as V6
except ImportError:  # 独立测试环境
    import anima_v4_pngmeta as PM
    import anima_v4_rules as R
    import catalog
    import manual
    import nodes_v6 as V6

_CHANGED_TICK = itertools.count()


def _json(raw, default):
    try:
        v = json.loads(raw) if str(raw or "").strip() else default
        return v
    except Exception:
        return default


class AnimaPromptStudio(V6.AnimaV4RandomPrompt):
    """提示词工坊主节点：random / manual / hybrid 三模式。"""

    @classmethod
    def INPUT_TYPES(cls):
        base = V6.AnimaV4RandomPrompt.INPUT_TYPES()
        # 深拷贝，避免改到 V6 的类级字典
        out = {}
        for section, fields in base.items():
            if isinstance(fields, dict):
                out[section] = dict(fields)
            else:
                out[section] = fields
        out.setdefault("optional", {})
        out["optional"]["mode"] = (
            ["manual", "hybrid", "random"],
            {"default": "manual",
             "tooltip": "manual=只用手选条目；hybrid=手选打底+随机补未覆盖段；"
                        "random=完全走 V6 随机引擎"},
        )
        out["optional"]["studio_json"] = (
            "STRING",
            {"default": "{}", "multiline": False,
             "tooltip": "面板保存的手选状态（一般不用手改）"},
        )
        out["optional"]["manual_text"] = (
            "STRING",
            {"default": "", "multiline": True,
             "tooltip": "额外手写补充，按逗号拼进正文"},
        )
        return out

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "report", "level", "cn_summary", "negative", "lora_json")
    FUNCTION = "generate"
    CATEGORY = V6.SECTION_NAME

    @classmethod
    def IS_CHANGED(cls, seed=-1, **kwargs):
        mode = str(kwargs.get("mode") or "manual").strip().lower()
        studio = str(kwargs.get("studio_json") or "")
        digest = zlib.crc32(studio.encode("utf-8"))
        try:
            seed_i = int(seed)
        except (TypeError, ValueError):
            seed_i = -1
        if seed_i < 0 and mode == "random":
            return f"rand:{time.time_ns()}:{next(_CHANGED_TICK)}"
        return (f"mode:{mode}|seed:{seed_i}|studio:{digest}"
                f"|level:{kwargs.get('nsfw_level')}|manual:{kwargs.get('manual_text')}"
                f"|state:{V6._global_state_fingerprint()}")

    def generate(self, **kwargs):
        mode = str(kwargs.pop("mode", "manual") or "manual").strip().lower()
        raw_studio = kwargs.pop("studio_json", "{}")
        manual_text = str(kwargs.pop("manual_text", "") or "")
        st = manual.parse_studio(raw_studio)
        st["mode"] = mode
        if manual_text.strip():
            st["extra_text"] = (str(st.get("extra_text") or "") + ", " + manual_text).strip(", ")
        res = manual.compose(st, kwargs)

        try:
            pm_state = PM.inject_metadata(
                kwargs.get("extra_pnginfo"), kwargs.get("prompt"), res["text"],
                self_ids={str(kwargs.get("unique_id"))}
                if kwargs.get("unique_id") is not None else frozenset(),
                version=V6._v3_version())
            V6._record_meta(pm_state)
        except Exception as exc:  # pragma: no cover
            print(f"[AnimaPromptStudio] 元数据注入失败（不影响出图）: {exc}")

        return (res["text"], res["report_text"], res["level_label"],
                res["cn_summary"], res.get("negative", ""),
                json.dumps(st.get("lora") or [], ensure_ascii=False))


class AnimaPromptStudioEncode:
    """把主节点输出的正向 / 负向提示词直接编码成 CONDITIONING。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "text": ("STRING", {"default": "", "multiline": True}),
                "negative": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "encode"
    CATEGORY = V6.SECTION_NAME

    def encode(self, clip, text, negative=""):
        def _enc(txt):
            tokens = clip.tokenize(str(txt or ""))
            return clip.encode_from_tokens_scheduled(tokens)
        return (_enc(text), _enc(negative))


class AnimaPromptStudioBoxes:
    """多提示词框：每框独立开关 / 排序，拼成一条。

    `boxes_json` 结构：[{"text": "...", "on": true, "title": "框 1"}]
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "boxes_json": ("STRING", {"default": "[]", "multiline": False}),
                "separator": ("STRING", {"default": ", ", "multiline": False}),
            },
            "optional": {
                "dedupe": ("BOOLEAN", {"default": True}),
                "tag_cap": ("INT", {"default": 0, "min": 0, "max": 200}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("text", "count", "report")
    FUNCTION = "compose"
    CATEGORY = V6.SECTION_NAME

    def compose(self, boxes_json, separator=", ", dedupe=True, tag_cap=0):
        boxes = _json(boxes_json, [])
        if isinstance(boxes, dict):
            boxes = boxes.get("boxes") or []
        parts = []
        for i, box in enumerate(boxes if isinstance(boxes, list) else []):
            if not isinstance(box, dict) or box.get("on") is False:
                continue
            txt = str(box.get("text") or "").strip()
            if not txt:
                continue
            parts.append((i, txt))
        sep = str(separator if separator is not None else ", ")
        # 以逗号为边界的去重；保留用户框内原样
        out, seen = [], set()
        for _i, txt in parts:
            for piece in txt.replace("\n", ",").split(","):
                p = piece.strip()
                if not p:
                    continue
                key = p.lower()
                if dedupe and key in seen:
                    continue
                seen.add(key)
                out.append(p)
        if tag_cap and len(out) > int(tag_cap):
            out = out[:int(tag_cap)]
        text = sep.join(out)
        report = (f"提示词框：启用 {len(parts)} 个 · 标签 {len(out)} 个"
                  f"{'（已截断到 %d）' % int(tag_cap) if tag_cap else ''}")
        return (text, len(out), report)


class AnimaPromptStudioBoxesEncode:
    """多提示词框 + CLIP 编码（对应 Tools 的 Prompt Plus）。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "boxes_json": ("STRING", {"default": "[]", "multiline": False}),
                "separator": ("STRING", {"default": ", ", "multiline": False}),
            },
            "optional": {
                "dedupe": ("BOOLEAN", {"default": True}),
                "tag_cap": ("INT", {"default": 0, "min": 0, "max": 200}),
            },
        }

    RETURN_TYPES = ("CONDITIONING", "STRING")
    RETURN_NAMES = ("conditioning", "text")
    FUNCTION = "encode"
    CATEGORY = V6.SECTION_NAME

    def encode(self, clip, boxes_json, separator=", ", dedupe=True, tag_cap=0):
        text, _n, _rep = AnimaPromptStudioBoxes().compose(
            boxes_json, separator, dedupe, tag_cap)
        tokens = clip.tokenize(text)
        return (clip.encode_from_tokens_scheduled(tokens), text)


class AnimaPromptStudioSelector:
    """通用标签选择器：画师 / 角色 / 服装 / 姿势 / 背景 / 任意 V6 段。

    picked_json 是目录条目数组（面板写入）；也可以在为空时按 seed 随机抽。
    """

    CATEGORIES = [
        "artist", "character", "v6char", "clothing", "v6outfit", "pose",
        "background", "quality", "community:qianteng", "community:raven",
        "community:composition", "my",
    ]
    CATEGORY_LABELS = {
        "artist": "画师", "character": "角色（Tools）", "v6char": "角色（V6）",
        "clothing": "服装（Tools）", "v6outfit": "服装（V6）", "pose": "姿势",
        "background": "背景", "quality": "质量词",
        "community:qianteng": "千藤的衣柜", "community:raven": "渡鸦的构图鉴",
        "community:composition": "凉夏的构图风格", "my": "我的 Tag",
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "category": (cls.CATEGORIES, {"default": "artist"}),
                "picked_json": ("STRING", {"default": "[]", "multiline": False}),
            },
            "optional": {
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
                "random_count": ("INT", {"default": 1, "min": 0, "max": 20}),
                "max_level": (["不限", "sfw", "suggestive", "explicit",
                               "hardcore", "extreme"], {"default": "不限"}),
                "separator": ("STRING", {"default": ", ", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("text", "count", "report")
    FUNCTION = "select"
    CATEGORY = V6.SECTION_NAME

    def select(self, category, picked_json="[]", seed=-1,
               random_count=1, max_level="不限", separator=", "):
        picked = _json(picked_json, [])
        if isinstance(picked, dict):
            picked = picked.get("items") or []
        ids = []
        for row in picked if isinstance(picked, list) else []:
            if isinstance(row, str):
                ids.append(row)
            elif isinstance(row, dict):
                if row.get("on") is False:
                    continue
                ids.append(row.get("id") or row.get("en"))
        rows = catalog.get_by_ids(ids) if ids else []

        if not rows and int(random_count or 0) > 0:
            lv_max = None
            if max_level != "不限":
                lv_max = manual.level_num(max_level)
            rows = catalog.sample(category, int(random_count), seed=seed,
                                  level_max=lv_max)

        texts = []
        for r in rows:
            for t in str(r.get("en") or "").replace("\n", ",").split(","):
                t = t.strip()
                if t:
                    texts.append(t)
        text = str(separator if separator is not None else ", ").join(texts)
        report = f"{self.CATEGORY_LABELS.get(category, category)}：{len(texts)} 个标签"
        return (text, len(texts), report)
