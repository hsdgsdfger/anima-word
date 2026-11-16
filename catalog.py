# -*- coding: utf-8 -*-
"""统一标签目录。

把四类来源汇成一张可检索、可分页的目录：

  1. V6 词库（15 段 / 57 字段 / 1134 选项，带逐项档位）
  2. V6 角色（2432，含本地缩略图）、场景搭配（524）、服装库（135）
  3. Anima-Tools 数据（画师 42197 / 角色 8000 / 服装 430 / 姿势 297 /
     背景 1087 / 社区库 6759）
  4. 用户自己的「我的 Tag」（ComfyUI/user/anima_prompt_studio/my_tags.json）

设计约束：
  · 目录只读；写操作在 routes 里单独处理。
  · 首次请求时建索引，之后走内存缓存。
  · 单个分类分页返回，避免一次把 4 万条画师塞给浏览器。
  · 不依赖 ComfyUI —— 测试环境没有 folder_paths 时自动退回插件目录。
"""
from __future__ import annotations

import json
import os
import random
import re
import threading
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data", "tools")
PRESET_DIR = os.path.join(HERE, "presets")

_LOCK = threading.RLock()
_CACHE = {"items": None, "meta": None, "by_id": None}

# 分类展示顺序。key 与前端约定一致；title 带 emoji，和 V6 面板的语气一致。
CATEGORY_GROUPS = [
    ("base", "基础词库", [
        ("quality", "✨ 质量与风格"),
        ("v6:count", "① 数量与身份"),
        ("v6:character", "① 角色"),
        ("v6:hair", "② 头发"),
        ("v6:face", "③ 五官与表情"),
        ("v6:body", "④ 身材与肤质"),
        ("v6:makeup", "⑤ 妆容与细节"),
        ("v6:cloth_sfw", "⑥ 服装（SFW）"),
        ("v6:pose_sfw", "⑦ 姿势与动作（SFW）"),
        ("v6:camera", "⑧ 镜头"),
        ("v6:scene", "⑨ 场景与环境"),
        ("v6:lighting", "⑩ 光影氛围"),
    ]),
    ("assets", "素材库", [
        ("v6char", "🎭 角色库（V6 · 2432）"),
        ("character", "🎭 角色库（Tools · 8000）"),
        ("artist", "🎨 画师（42197）"),
        ("v6outfit", "👗 服装库（V6 · 135）"),
        ("clothing", "👗 服装（Tools · 430）"),
        ("pose", "🧘 姿势（Tools · 297）"),
        ("background", "🏞 背景（Tools · 1087）"),
    ]),
    ("scenes", "场景与构图", [
        ("scene_sfw", "🏙 场景搭配"),
        ("scene_nsfw", "🔞 场景搭配"),
        ("scene_pose", "🧎 姿势场景"),
        ("scene_art", "🎨 艺术构图"),
        ("scene_weapon", "⚔️ 武器场景"),
        ("scene_near", "🔍 特写搭配"),
    ]),
    ("community", "社区 Tag 库", [
        ("community:qianteng", "👗 千藤的衣柜"),
        ("community:raven", "🪶 渡鸦的构图鉴"),
        ("community:composition", "🌇 凉夏之夜的构图风格"),
    ]),
    ("adult", "成人向（受档位闸门约束）", [
        ("v6:cloth_nsfw", "🔞 服装状态"),
        ("v6:pose_nsfw", "🔞 体位与性行为"),
        ("v6:special_nsfw", "🔞 特殊主题"),
        ("v6:canon", "🔞 法典验证场景"),
    ]),
    ("mine", "我的", [
        ("my", "⭐ 我的 Tag"),
    ]),
]

SECTION_TITLES = {
    "count": "① 数量与身份",
    "hair": "② 头发",
    "face": "③ 五官与表情",
    "body": "④ 身材与肤质",
    "makeup": "⑤ 妆容与细节",
    "cloth_sfw": "⑥ 服装（SFW）",
    "pose_sfw": "⑦ 姿势与动作（SFW）",
    "camera": "⑧ 镜头",
    "scene": "⑨ 场景与环境",
    "lighting": "⑩ 光影氛围",
    "cloth_nsfw": "🔞 服装状态（NSFW）",
    "pose_nsfw": "🔞 体位与性行为（NSFW）",
    "special_nsfw": "🔞 特殊主题（NSFW）",
    "canon": "🔞 法典验证场景（NSFW）",
    "nl_block": "⑫ 自然语言补位",
}

# field_key -> 手选输出槽位。槽位顺序沿用 V6 的 SLOTS，
# 这样"按槽位排序"出来的结果和随机引擎的观感一致。
SLOT_BY_FIELD = {
    "count": "character",
    "role": "character",
    "hair_len": "appearance", "hair_color": "appearance", "hair_curl": "appearance",
    "hair_tie": "appearance", "hair_bangs": "appearance", "hair_fx": "appearance",
    "hair_acc": "appearance",
    "eyes_color": "appearance", "emotion": "appearance", "eye_gaze": "appearance",
    "mouth": "appearance", "figure": "appearance", "skin": "appearance",
    "leg": "appearance", "skin_detail": "appearance", "makeup": "appearance",
    "nails": "appearance",
    "outfit": "clothing", "top": "clothing", "bottom": "clothing",
    "socks": "clothing", "sock_color": "clothing", "shoes": "clothing",
    "accessory": "clothing", "cloth_mat": "clothing", "cloth_color": "clothing",
    "cloth_state_sfw": "clothing", "cloth_state_nsfw": "clothing",
    "pose_base": "pose", "arms_hands": "pose", "action": "pose",
    "pose_risque": "pose", "n_act": "pose", "n_pos": "pose",
    "shot_size": "camera", "dof": "camera", "viewpoint": "camera",
    "angle": "camera",
    "place": "scene", "weather": "scene", "comp": "scene",
    "light_fx": "lighting", "texture_fx": "lighting",
    "n_theme": "other", "n_orgasm": "other", "n_cum": "other",
    "n_canon": "scene", "n_extra": "other",
}

SLOT_ORDER = {
    "quality": 0, "artist": 1, "character": 2, "appearance": 3,
    "clothing": 4, "pose": 5, "camera": 6, "scene": 7,
    "lighting": 8, "other": 9,
}


def _load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default if default is not None else {}


def _clean(text):
    return re.sub(r"[\s_]+", " ", str(text or "").strip().lower())


def _item(cat, en, zh="", slot="other", level=0, src="", thumb="",
          tags=None, extra=None, item_id=None):
    en = str(en or "").strip()
    if not en and not zh:
        return None
    try:
        level = max(0, min(4, int(level or 0)))
    except (TypeError, ValueError):
        level = 0
    return {
        "id": item_id or f"{cat}:{en[:80]}:{zh[:40]}",
        "cat": cat,
        "en": en,
        "zh": zh or en,
        "slot": slot,
        "level": level,
        "src": src,
        "thumb": thumb or "",
        "tags": list(tags or []),
        "extra": dict(extra or {}),
        "_q": (en + " " + (zh or "")).lower(),
    }


def _v6_section_items():
    """V6 词库：每个选项一条。档位来自 R.option_level（与引擎同源）。"""
    try:
        from . import anima_v4_rules as R
    except ImportError:  # 独立测试环境
        import anima_v4_rules as R

    out = []
    for sec in R.sections():
        sid = sec["id"]
        if sid == "nl_block":
            continue  # 自然语言补位没有选项池
        cat = f"v6:{sid}"
        for fld in sec.get("fields", []):
            key = fld["key"]
            slot = SLOT_BY_FIELD.get(key, "other")
            for zh, en in fld.get("opts", []):
                en = str(en or "").strip()
                if not en:
                    continue
                try:
                    lv = R.option_level(key, en)
                except Exception:
                    lv = 0
                item = _item(cat, en, zh, slot, lv, "v6",
                             item_id=f"v6:{key}:{en}")
                if item:
                    item["extra"] = {"field": key, "section": sid,
                                     "field_label": fld.get("lab", "")}
                    out.append(item)

    # 角色库单独一个分类（V6 面板已有，但自由选择里也要能搜）
    chars = R.characters_data().get("characters") or []
    for ch in chars:
        trigger = str(ch.get("trigger") or ch.get("name") or "").strip()
        if not trigger:
            continue
        try:
            lv = R.tag_level(trigger)
        except Exception:
            lv = 0
        item = _item("v6char", trigger, ch.get("zh") or ch.get("name") or trigger,
                     "character", lv, "v6",
                     thumb=f"/anima-prompt-studio/thumb/{ch.get('thumb') or ch.get('tag')}",
                     tags=ch.get("tags") or [],
                     extra={"work": ch.get("work", ""), "pop": ch.get("pop", 0),
                            "tag": ch.get("tag", ""), "trigger": trigger},
                     item_id=f"v6char:{ch.get('tag') or trigger}")
        if item:
            out.append(item)
    return out


def _v6_scene_items():
    try:
        from . import anima_v4_rules as R
    except ImportError:
        import anima_v4_rules as R

    out = []
    for sc in R.scene_list():
        group = str(sc.get("group") or "sfw")
        cat = {
            "sfw": "scene_sfw", "nsfw": "scene_nsfw", "near": "scene_near",
            "pose": "scene_pose", "art": "scene_art", "weapon": "scene_weapon",
        }.get(group, "scene_sfw")
        tags = []
        fields = sc.get("tags") or {}
        for _k, v in fields.items():
            if str(v or "").strip():
                tags.extend(str(v).split(","))
        for chunk in str(sc.get("extra") or "").split(","):
            if chunk.strip():
                tags.append(chunk.strip())
        en = ", ".join(t for t in (x.strip().lower() for x in tags) if t)
        item = _item(cat, en, sc.get("zh") or sc.get("id"), "scene",
                     int(sc.get("level") or 0), "v6",
                     tags=tags,
                     extra={"scene_id": sc.get("id"), "group": group,
                            "desc": sc.get("desc", ""), "theme": sc.get("theme", ""),
                            "count_lock": sc.get("count_lock", ""),
                            "scene_nl": sc.get("scene_nl", "")},
                     item_id=f"scene:{sc.get('id')}")
        if item:
            out.append(item)
    return out


def _v6_outfit_items():
    try:
        from . import anima_v4_rules as R
    except ImportError:
        import anima_v4_rules as R

    out = []
    for it in (R.library_data().get("items") or []):
        tags = [str(t).strip() for t in (it.get("tags") or []) if str(t).strip()]
        en = ", ".join(tags)
        item = _item("v6outfit", en, it.get("zh") or it.get("id"), "clothing",
                     int(it.get("level") or 0), "v6", tags=tags,
                     extra={"outfit_id": it.get("id"), "cat": it.get("cat", ""),
                            "fields": it.get("fields") or {}},
                     item_id=f"outfit:{it.get('id')}")
        if item:
            out.append(item)
    return out


def _tools_items():
    out = []

    artists = _load_json(os.path.join(DATA_DIR, "artists.json"), [])
    for a in artists:
        name = str(a.get("name") or "").strip()
        if not name:
            continue
        item = _item("artist", f"@{name}", name, "artist", 0, "tools",
                     extra={"post_count": a.get("post_count", 0),
                            "artist_id": a.get("id", "")},
                     item_id=f"artist:{a.get('id') or name}")
        if item:
            out.append(item)

    # Tools 角色：lite 表 + 官方特征表按 `name||copyright` 合并
    lite = _load_json(os.path.join(DATA_DIR, "characters_lite.json"), [])
    official = _load_json(os.path.join(DATA_DIR, "character_official.json"), {})
    for c in lite:
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        copyright_ = str(c.get("copyright") or "").strip()
        key = f"{name}||{copyright_}".lower()
        rec = official.get(key) or official.get(f"{name}||{copyright_}") or {}
        trigger = str(rec.get("trigger") or (f"{name}, {copyright_}" if copyright_ else name))
        tags = rec.get("tags") or []
        item = _item("character", trigger, name, "character", 0, "tools",
                     tags=tags,
                     extra={"work": copyright_, "pop": c.get("post_count", 0),
                            "gender": c.get("gender", ""), "hair": c.get("hair", ""),
                            "eye": c.get("eye", ""), "trigger": trigger},
                     item_id=f"tools_char:{name}||{copyright_}")
        if item:
            out.append(item)

    clothing = _load_json(os.path.join(DATA_DIR, "clothing.json"), [])
    for c in clothing:
        tags = str(c.get("tags") or "").strip().rstrip(",")
        item = _item("clothing", tags, c.get("name_zh") or c.get("name"), "clothing",
                     0, "tools", thumb=c.get("preview", ""),
                     extra={"name": c.get("name", ""), "categories": c.get("categories") or [],
                            "traits": c.get("traits") or [], "note": c.get("note", "")},
                     item_id=f"clothing:{c.get('id')}")
        if item:
            out.append(item)

    poses = _load_json(os.path.join(DATA_DIR, "poses.json"), [])
    for p in poses:
        tags = str(p.get("tags") or "").strip().rstrip(",")
        item = _item("pose", tags, p.get("name_zh") or p.get("name"), "pose",
                     0, "tools", thumb=p.get("preview", ""),
                     extra={"name": p.get("name", ""), "categories": p.get("categories") or [],
                            "traits": p.get("traits") or [], "note": p.get("note", "")},
                     item_id=f"pose:{p.get('id')}")
        if item:
            out.append(item)

    backgrounds = _load_json(os.path.join(DATA_DIR, "backgrounds.json"), [])
    for b in backgrounds:
        tags = str(b.get("tags") or "").strip().rstrip(",")
        item = _item("background", tags, b.get("name_zh") or b.get("name"), "scene",
                     0, "tools", thumb=b.get("preview", ""),
                     extra={"name": b.get("name", ""), "categories": b.get("categories") or [],
                            "traits": b.get("traits") or [], "note": b.get("note", "")},
                     item_id=f"background:{b.get('id')}")
        if item:
            out.append(item)

    for filename, cat, srcname in (
        ("qianteng.json", "community:qianteng", "千藤的衣柜"),
        ("raven.json", "community:raven", "渡鸦的构图鉴"),
        ("composition_style.json", "community:composition", "凉夏之夜的构图风格"),
    ):
        rows = _load_json(os.path.join(DATA_DIR, filename), [])
        for r in rows:
            tags = str(r.get("tags") or "").strip().rstrip(",")
            item = _item(cat, tags, r.get("name") or tags[:40], "other",
                         0, "tools", thumb=r.get("preview", ""),
                         extra={"name": r.get("name", ""), "library": srcname,
                                "categories": r.get("categories") or [],
                                "traits": r.get("traits") or [],
                                "note": r.get("note", "")},
                         item_id=f"{cat}:{r.get('id')}")
            if item:
                out.append(item)

    return out


def _user_items():
    """我的 Tag。结构：{categories:[{name, zh, children?}], entries:[{id, cat, en, zh, ...}]}"""
    path = user_data_path("my_tags.json")
    data = _load_json(path, {})
    out = []
    for e in (data.get("entries") or []):
        en = str(e.get("en") or "").strip()
        if not en:
            continue
        item = _item("my", en, e.get("zh") or en, e.get("slot") or "other",
                     e.get("level") or 0, "my",
                     tags=[t.strip() for t in en.split(",") if t.strip()],
                     extra={"cat": e.get("cat", "我的分类"), "note": e.get("note", ""),
                            "cover": e.get("cover", "")},
                     item_id=f"my:{e.get('id') or en}")
        if item:
            out.append(item)
    return out


def user_data_path(filename=""):
    """用户数据目录：优先 ComfyUI/user/anima_prompt_studio，退回归插件目录。"""
    base = ""
    try:
        import folder_paths
        base = folder_paths.get_user_directory()
    except Exception:
        base = ""
    if not base:
        base = os.path.join(HERE, "user_data")
    root = os.path.join(base, "anima_prompt_studio")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, filename) if filename else root


def _build():
    items = []
    items.extend(_v6_section_items())
    items.extend(_v6_scene_items())
    items.extend(_v6_outfit_items())
    items.extend(_tools_items())
    items.extend(_user_items())

    # 质量词是"手选"里最常用的一类，单独提出来
    for en, zh, lv in (
        ("masterpiece", "杰作", 0), ("best quality", "最佳质量", 0),
        ("high quality", "高质量", 0), ("score_7", "评分 7", 0),
        ("score_8_up", "评分 8+", 0), ("score_9", "评分 9", 0),
        ("very aesthetic", "非常美观", 0), ("absurdres", "超高分辨率", 0),
    ):
        item = _item("quality", en, zh, "quality", lv, "builtin",
                     item_id=f"quality:{en}")
        if item:
            items.append(item)

    # 去重：同一分类里 en 相同的只留第一条（V6 选项里会有别名重复）。
    # 角色库例外：不同角色可能共享同一个 trigger（同作品换装/形态），
    # 按 id 去重才不会把角色吞掉。
    seen = set()
    dedup = []
    for it in items:
        key = (it["id"],) if it["cat"] in ("v6char", "character") else (
            it["cat"], _clean(it["en"]))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(it)
    return dedup


def _build_meta(items):
    counts = {}
    for it in items:
        counts[it["cat"]] = counts.get(it["cat"], 0) + 1
    groups = []
    for gid, title, cats in CATEGORY_GROUPS:
        rows = []
        for key, label in cats:
            n = counts.get(key, 0)
            if not n:
                continue
            rows.append({"key": key, "label": label, "count": n})
        if rows:
            groups.append({"id": gid, "title": title, "cats": rows})
    # 没进白名单但实际存在的分类（例如未来新增的 V6 段）兜底展示
    known = {k for _g, _t, cats in CATEGORY_GROUPS for k, _l in cats}
    extra = [{"key": k, "label": k, "count": v} for k, v in sorted(counts.items())
             if k not in known]
    if extra:
        groups.append({"id": "other", "title": "其他", "cats": extra})
    return {
        "total": len(items),
        "groups": groups,
        "counts": counts,
        "slots": list(SLOT_ORDER.keys()),
        "slot_order": SLOT_ORDER,
        "levels": [
            {"num": 0, "key": "sfw", "label": "0 · 全年龄"},
            {"num": 1, "key": "suggestive", "label": "1 · 擦边"},
            {"num": 2, "key": "explicit", "label": "2 · 成人"},
            {"num": 3, "key": "hardcore", "label": "3 · 过激"},
            {"num": 4, "key": "extreme", "label": "4 · 极端"},
        ],
    }


def ensure():
    with _LOCK:
        if _CACHE["items"] is None:
            items = _build()
            _CACHE["items"] = items
            _CACHE["meta"] = _build_meta(items)
            _CACHE["by_id"] = {it["id"]: it for it in items}
        return _CACHE


def clear_cache():
    with _LOCK:
        _CACHE["items"] = None
        _CACHE["meta"] = None
        _CACHE["by_id"] = None


def meta():
    return ensure()["meta"]


def _norm_query(q):
    q = str(q or "").strip().lower()
    # NFKC 让全角字符也能匹配
    return unicodedata.normalize("NFKC", q)


def items(cat="", q="", page=1, limit=60, level_max=None, src=""):
    data = ensure()
    all_items = data["items"]
    q = _norm_query(q)
    cat = str(cat or "").strip()
    src = str(src or "").strip()

    rows = all_items
    if cat and cat != "all":
        rows = [it for it in rows if it["cat"] == cat]
    if src:
        rows = [it for it in rows if it["src"] == src]
    if q:
        rows = [it for it in rows if q in it["_q"]]
    if level_max is not None:
        try:
            lm = int(level_max)
            rows = [it for it in rows if 0 <= it["level"] <= lm]
        except (TypeError, ValueError):
            pass

    total = len(rows)
    try:
        page = max(1, int(page))
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        page, limit = 1, 60
    start = (page - 1) * limit
    end = start + limit
    out = []
    for it in rows[start:end]:
        row = {k: v for k, v in it.items() if not k.startswith("_")}
        out.append(row)
    return {"total": total, "page": page, "limit": limit, "items": out}


def sample(cat="", n=1, seed=None, level_max=None, src=""):
    """从整个分类里随机抽样（不是只抽第一页）。

    选择器节点的 `random_count` 需要的是全分类随机；先分页再 sample 会让
    42k 画师里只有前 500 个有概率被抽到，长期看等于固定池子。
    """
    data = ensure()
    cat = str(cat or "").strip()
    src = str(src or "").strip()
    rows = data["items"]
    if cat and cat != "all":
        rows = [it for it in rows if it["cat"] == cat]
    if src:
        rows = [it for it in rows if it["src"] == src]
    if level_max is not None:
        try:
            lm = int(level_max)
            rows = [it for it in rows if 0 <= it["level"] <= lm]
        except (TypeError, ValueError):
            pass
    try:
        n = max(0, int(n))
    except (TypeError, ValueError):
        n = 0
    if not rows or not n:
        return []
    rng = random.Random(seed)
    if seed is not None:
        try:
            if int(seed) < 0:
                rng = random.Random()
        except (TypeError, ValueError):
            rng = random.Random()
    picked = rng.sample(rows, min(n, len(rows)))
    return [{k: v for k, v in it.items() if not k.startswith("_")}
            for it in picked]


def get_by_ids(ids):
    data = ensure()
    by_id = data["by_id"]
    out = []
    for i in ids or []:
        rec = by_id.get(str(i))
        if rec:
            out.append({k: v for k, v in rec.items() if not k.startswith("_")})
    return out


def find(cat, en=None, zh=None):
    data = ensure()
    for it in data["items"]:
        if cat and it["cat"] != cat:
            continue
        if en is not None and _clean(it["en"]) == _clean(en):
            return {k: v for k, v in it.items() if not k.startswith("_")}
        if zh is not None and it["zh"] == zh:
            return {k: v for k, v in it.items() if not k.startswith("_")}
    return None
