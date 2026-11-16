# -*- coding: utf-8 -*-
"""手选 / 混合出词引擎。

三种模式：
  · random  —— 完全交给 V6 引擎（与 V6 节点逐字节一致）
  · manual  —— 只用用户勾选的条目，按手选顺序或槽位顺序拼
  · hybrid  —— 手选条目先占位，未覆盖的段落交给 V6 随机补全

手选状态存在节点控件 `studio_json` 里（随工作流保存），结构：
{
  "version": 1,
  "mode": "manual",
  "items": [{"id","cat","en","zh","slot","w","on","src"}],
  "order": "slot" | "custom",
  "quality_prefix": "",
  "extra_text": "",
  "negative_preset": "standard",
  "negative_extra": "",
  "ui": {...}
}
"""
from __future__ import annotations

import json
import re

try:
    from . import anima_v4_rules as R
except ImportError:  # 独立测试环境
    import anima_v4_rules as R
try:
    from .negative import build_negative
except ImportError:
    from negative import build_negative

DEFAULT_STUDIO = {
    "version": 1,
    "mode": "manual",
    "items": [],
    "order": "slot",
    "quality_prefix": "",
    "extra_text": "",
    "negative_preset": "standard",
    "negative_extra": "",
    "lora": [],
    "ui": {},
}

# 手选条目覆盖了哪些 V6 段 —— 混合模式下这些段不再随机。
CAT_TO_SECTIONS = {
    "v6:count": {"count"},
    # 角色条目本身就带官方发色/瞳色/体型；混合模式下必须把这些段一起占住，
    # 否则随机角色会再补一个角色并注入冲突外貌。
    "v6char": {"count", "hair", "face", "body", "makeup"},
    "character": {"count", "hair", "face", "body", "makeup"},
    "v6:character": {"count"},
    "v6:hair": {"hair"},
    "v6:face": {"face"},
    "v6:body": {"body"},
    "v6:makeup": {"makeup"},
    "v6:camera": {"camera"},
    "v6:scene": {"scene"},
    "v6:lighting": {"lighting"},
    "background": {"scene"},
    "v6outfit": {"cloth_sfw", "cloth_nsfw"},
    "clothing": {"cloth_sfw"},
    "v6:cloth_sfw": {"cloth_sfw"},
    "v6:cloth_nsfw": {"cloth_nsfw"},
    "v6:pose_sfw": {"pose_sfw"},
    "pose": {"pose_sfw"},
    "v6:pose_nsfw": {"pose_nsfw"},
    "v6:special_nsfw": {"special_nsfw"},
    "v6:canon": {"canon"},
    "scene_sfw": {"scene", "camera", "lighting"},
    "scene_pose": {"scene", "pose_sfw"},
    "scene_art": {"scene", "camera", "lighting"},
    "scene_weapon": {"scene", "pose_sfw"},
    "scene_near": {"scene", "camera", "lighting"},
    "scene_nsfw": {"scene", "pose_nsfw"},
}

LEVEL_MAP = {"sfw": 0, "suggestive": 1, "explicit": 2,
             "hardcore": 3, "extreme": 4, "any": 4}

# 与 V6 的 SLOTS 同序；quality / artist / other 是手选额外槽位。
SLOT_ORDER = {name: i for i, name in enumerate(R.SLOTS)}
SLOT_ORDER.update({"quality": -1, "artist": 0.5, "other": len(R.SLOTS)})


def parse_studio(raw):
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(str(raw or "{}"))
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    out = dict(DEFAULT_STUDIO)
    out["items"] = data.get("items") if isinstance(data.get("items"), list) else []
    for key in ("mode", "order", "quality_prefix", "extra_text",
                "negative_preset", "negative_extra"):
        if key in data:
            out[key] = data[key]
    if isinstance(data.get("lora"), list):
        out["lora"] = data["lora"]
    if isinstance(data.get("ui"), dict):
        out["ui"] = data["ui"]
    return out


def level_num(value):
    if isinstance(value, (int, float)):
        return max(0, min(4, int(value)))
    key = str(value or "").strip().lower()
    if key in LEVEL_MAP:
        return LEVEL_MAP[key]
    try:
        return max(0, min(4, int(key)))
    except (TypeError, ValueError):
        return 0


def _clean_tag(t):
    return re.sub(r"[\s_]+", " ", str(t or "").strip().lower()).strip(" ,")


def _split_tags(text):
    return [_clean_tag(t) for t in str(text or "").replace("\n", ",").split(",")
            if _clean_tag(t)]


def normalize_items(rows):
    """只保留字段完整、未禁用的条目。"""
    out = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        en = str(row.get("en") or "").strip()
        if not en:
            continue
        if row.get("on") is False:
            continue
        try:
            w = float(row.get("w", 1.0))
        except (TypeError, ValueError):
            w = 1.0
        w = max(0.1, min(3.0, w))
        out.append({
            "id": str(row.get("id") or en),
            "cat": str(row.get("cat") or ""),
            "en": en,
            "zh": str(row.get("zh") or ""),
            "slot": str(row.get("slot") or "other"),
            "w": w,
            "src": str(row.get("src") or ""),
        })
    return out


def _slot_key(item):
    return SLOT_ORDER.get(item.get("slot") or "other", SLOT_ORDER["other"])


def _ordered(items, order):
    if str(order or "").strip() == "custom":
        return list(items)
    # 槽位排序：稳定排序，同槽位内保留用户手选顺序
    return sorted(items, key=_slot_key)


def _join_quality(prefix):
    return [t for t in _split_tags(prefix) if t]


def _manual_report(final, lv, lv_key, report, fixes):
    """手选专用报告：不拿"随机模板"的标签数量 / 质量词去吓人。"""
    F = [c for c in report["F"] if c["id"] not in ("F1", "F2")]
    ok_f = sum(1 for c in F if c["ok"])
    lines = [
        "模式     : 手选（只输出勾选条目）",
        f"档位     : {R.level_label(lv_key)}（上限 {lv}）",
        f"标签数   : {len(final)}",
        f"实际落档 : {report['real_level']} {report['real_level_label']}",
        f"检查     : 致命项 {ok_f}/{len(F)} · 风格项 "
        f"{report['ok_s']}/{report['total_s']}",
        "说明     : 手选模式不检查标签数量与质量词（这两项由你决定）",
    ]
    if fixes:
        lines.append("")
        lines.append(f"── 已自动修复 {len(fixes)} 项 ──")
        for f in fixes:
            lines.append("  · " + f)
    bad = [c for c in F if not c["ok"]]
    if bad:
        lines.append("")
        lines.append("── 需要注意 ──")
        for c in bad:
            lines.append(f"  [!!] {c['id']} {c['name']} —— {c['note']}")
    return "\n".join(lines)


def compose_manual(items, level="sfw", order="slot", quality_prefix="",
                   extra_text="", weight_style="paren", extra_body=""):
    """纯手选：只输出用户点名的标签。"""
    lv_key = R.resolve_level(level)
    lv = R.LEVEL_NUM[lv_key]
    items = normalize_items(items)
    ordered = _ordered(items, order)

    raw = []
    weight_by_tag = {}
    zh_bits = []
    for it in ordered:
        for t in _split_tags(it["en"]):
            raw.append(t)
            weight_by_tag[t] = max(weight_by_tag.get(t, 0.0), float(it["w"]))
        if it.get("zh"):
            zh_bits.append(it["zh"])

    prefix = _join_quality(quality_prefix)
    raw = prefix + raw
    raw.extend(_split_tags(extra_text))

    tags, fixes = R.repair(raw, lv)
    # repair 之后按原始权重重新套括号；质量前缀不套
    final = _apply_weights(tags, weight_by_tag, weight_style)
    if extra_body:
        final.extend(_split_tags(extra_body))

    state, report = R.check_text(final, lv)
    text = ", ".join(final)
    rep = _manual_report(final, lv, lv_key, report, fixes)
    return {
        "text": text,
        "tags": final,
        "raw_tags": tags,
        "level": lv_key,
        "level_num": lv,
        "level_label": R.level_label(lv_key),
        "cn_summary": "，".join(zh_bits) if zh_bits else "（手选）",
        "report_text": rep,
        "report": rep,          # 节点 report 输出要的是可读文本
        "report_detail": report,
        "fixes": fixes,
        "counts": {"manual": len(items), "total": len(final)},
    }


def covered_sections(items):
    out = set()
    for it in normalize_items(items):
        out.update(CAT_TO_SECTIONS.get(it.get("cat") or "", set()))
        # 自定义 / 我的 Tag：按字段名猜
        field = (it.get("cat") or "").split(":")[-1]
        if field in R.section_ids():
            out.add(field)
    return out


def _manual_weight_map(items):
    """手选标签 -> 最大手选权重；混合合并后再套回括号。"""
    out = {}
    for it in normalize_items(items):
        for t in _split_tags(it.get("en") or ""):
            out[t] = max(out.get(t, 0.0), float(it.get("w") or 1.0))
    return out


def _apply_weights(tags, weight_by_tag, weight_style="paren"):
    final = []
    for t in tags:
        w = float(weight_by_tag.get(t, 1.0))
        if str(weight_style) == "plain" or abs(w - 1.0) < 0.001:
            final.append(t)
        else:
            final.append(f"({t}:{w:g})")
    return final


def _manual_has_character(items):
    """手选里是否点名了具体角色（角色卡 / V6 角色库）。"""
    for it in normalize_items(items):
        if (it.get("cat") or "") in ("v6char", "character"):
            return True
    return False


def _manual_has_appearance(items):
    """手选里是否点名了外貌标签（发色/瞳色/体型/妆容等）。"""
    for it in normalize_items(items):
        if (it.get("slot") or "") == "appearance":
            return True
        if (it.get("cat") or "") in ("v6:hair", "v6:face", "v6:body", "v6:makeup"):
            return True
    return False


def compose_hybrid(items, draw_kwargs, level="sfw", order="slot",
                   quality_prefix="", extra_text="", weight_style="paren",
                   extra_body=""):
    """手选打底 + V6 随机补全未覆盖的段。"""
    items = normalize_items(items)
    covered = covered_sections(items)
    base = compose_manual(items, level=level, order=order,
                          quality_prefix=quality_prefix,
                          extra_text=extra_text, weight_style=weight_style,
                          extra_body="")
    # 从 kwargs 里去掉手选已覆盖的段
    disabled = set(str(draw_kwargs.get("disabled_sections") or "").replace(
        "\n", ",").replace(" ", ",").split(","))
    disabled.discard("")
    disabled |= covered
    kwargs = dict(draw_kwargs)
    kwargs["disabled_sections"] = ",".join(sorted(disabled))
    # V6 的随机角色会带官方发色/瞳色/体型（appearance_follow），即使对应段被禁用
    # 也会从角色侧注入；手选点名角色或外貌时，混合模式必须关掉随机角色，
    # 否则会出现“手选初音 + 随机角色 + 冲突发色”。
    if _manual_has_character(items) or _manual_has_appearance(items):
        kwargs["role_pick"] = False
        kwargs["appearance_follow"] = False
        kwargs["selected_roles"] = ""
        kwargs["force_role"] = ""
    # extra_body 只在这里合并一次，避免节点补充词在随机结果和最终结果里出现两次
    kwargs["extra_body"] = ""
    drawn = draw_from_kwargs(kwargs)

    # 合并：手选在前，随机补在后；去重后统一修复
    weight_by_tag = _manual_weight_map(items)
    merged = list(base.get("raw_tags") or base["tags"]) + _split_tags(drawn["text"])
    merged.extend(_split_tags(extra_body))
    lv_key = R.resolve_level(level)
    lv = R.LEVEL_NUM[lv_key]
    tags, fixes = R.repair(merged, lv)
    # 手选权重在合并阶段保留；随机标签按 1.0 处理
    final = _apply_weights(tags, weight_by_tag, weight_style)
    state, report = R.check_text(final, lv)
    rep = R.format_check_report(final, lv, report, fixes=fixes,
                                level_label_txt=R.level_label(lv_key))
    cn = base["cn_summary"]
    if drawn.get("cn_summary"):
        cn = cn + "；随机补：" + drawn["cn_summary"]
    return {
        "text": ", ".join(final),
        "tags": final,
        "level": lv_key,
        "level_num": lv,
        "level_label": R.level_label(lv_key),
        "cn_summary": cn,
        "report_text": rep,
        "report": rep,          # 节点 report 输出要的是可读文本
        "report_detail": report,
        "fixes": fixes,
        "counts": {"manual": len(items), "drawn": len(drawn["tags"]),
                   "total": len(final), "covered": sorted(covered)},
    }


def draw_from_kwargs(kwargs):
    """把 V6 节点控件参数翻译成 R.draw，返回原始结果。"""
    weights_json = kwargs.get("weights_json") or ""
    _forced = {}
    try:
        raw = json.loads(weights_json) if str(weights_json).strip() else {}
        f = raw.get("forced") or {}
        if isinstance(f, dict):
            _forced = {str(k): str(v) for k, v in f.items()
                       if v is not None and str(v).strip() != ""}
    except Exception:
        _forced = {}

    enabled = set(R.section_ids())
    for chunk in str(kwargs.get("disabled_sections") or "").replace(
            "\n", ",").replace(" ", ",").split(","):
        c = chunk.strip()
        if c:
            enabled.discard(c)

    return R.draw(
        level=kwargs.get("nsfw_level") or "sfw",
        seed=kwargs.get("seed", -1),
        base_prob=kwargs.get("base_prob") or R.DEFAULT_BASE_PROB,
        weights=R.parse_weights(weights_json),
        enabled_sections=enabled,
        locks=set(str(kwargs.get("lock_fields") or "").replace(
            "\n", ",").split(",")) - {""},
        tag_cap=kwargs.get("tag_cap") or "自动",
        force_role=str(kwargs.get("force_role") or "").strip(),
        extra_body=str(kwargs.get("extra_body") or ""),
        appearance_follow=bool(kwargs.get("appearance_follow", True)),
        selected_roles=R.parse_selected_roles(kwargs.get("selected_roles") or ""),
        big_breasts=bool(kwargs.get("big_breasts", False)),
        breast_size=str(kwargs.get("breast_size") or "不指定"),
        role_works=str(kwargs.get("role_works") or "").strip(),
        outfit_style=str(kwargs.get("outfit_style") or "随机"),
        role_fav_only=bool(kwargs.get("role_fav_only", False)),
        hair_follow=bool(kwargs.get("hair_follow", True)),
        hair_picks={
            "hair_len": str(kwargs.get("hair_len_pick") or "").strip(),
            "hair_tie": str(kwargs.get("hair_tie_pick") or "").strip(),
            "hair_curl": str(kwargs.get("hair_curl_pick") or "").strip(),
            "hair_acc": str(kwargs.get("hair_acc_pick") or "").strip(),
        },
        role_pick=bool(kwargs.get("role_pick", True)),
        scene_pick=bool(kwargs.get("scene_pick", False)),
        forced=_forced,
        dry_skin_filter=bool(kwargs.get("dry_skin_filter", False)),
        dry_skin_groups=str(kwargs.get("dry_skin_groups") or "").strip(),
        dry_skin_tags=str(kwargs.get("dry_skin_tags") or "").strip(),
        duo_role_fill=bool(kwargs.get("duo_role_fill", True)),
        pick_pool_mode=str(kwargs.get("pick_pool_mode") or "").strip(),
        pick_pool_ids=str(kwargs.get("pick_pool_ids") or "").strip(),
    )


def compose(studio, kwargs):
    """统一入口：按 studio["mode"] 分发，返回 text/report/level/cn/negative。"""
    st = parse_studio(studio)
    mode = str(st.get("mode") or "manual").strip().lower()
    level = kwargs.get("nsfw_level") or "sfw"
    items = st.get("items") or []
    order = st.get("order") or "slot"
    qp = st.get("quality_prefix") or ""
    extra_text = st.get("extra_text") or ""
    extra_body = str(kwargs.get("extra_body") or "")

    if mode == "random":
        drawn = draw_from_kwargs(kwargs)
        res = {
            "text": drawn["text"],
            "tags": drawn["tags"],
            "raw_tags": drawn["tags"],
            "level": drawn["level"],
            "level_num": drawn["level_num"],
            "level_label": drawn["level_label"],
            "cn_summary": drawn["cn_summary"],
            "report_text": R.format_report(drawn),
            "report": drawn["report"],
            "fixes": [],
            "counts": {"drawn": len(drawn["tags"])},
        }
        res["negative"] = build_negative(
            drawn["text"], drawn["level_num"],
            preset=st.get("negative_preset") or "standard",
            extra=st.get("negative_extra") or "")
        return res

    if mode == "hybrid":
        res = compose_hybrid(items, kwargs, level=level, order=order,
                             quality_prefix=qp, extra_text=extra_text,
                             extra_body=extra_body)
    else:
        res = compose_manual(items, level=level, order=order,
                             quality_prefix=qp, extra_text=extra_text,
                             extra_body=extra_body)

    lv = res["level_num"]
    res["negative"] = build_negative(
        res["text"], lv,
        preset=st.get("negative_preset") or "standard",
        extra=st.get("negative_extra") or "")
    return res
