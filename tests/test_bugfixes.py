# -*- coding: utf-8 -*-
"""8 项 bug 报告的最小回归测试。

运行：
    python tests/test_bugfixes.py
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

from smoke_backend import PKG, load_plugin  # noqa: E402

mod = load_plugin()
manual = importlib.import_module(PKG + ".manual")
catalog = importlib.import_module(PKG + ".catalog")
negative = importlib.import_module(PKG + ".negative")
rules = importlib.import_module(PKG + ".anima_v4_rules")
style = importlib.import_module(PKG + ".anima_v4_outfit_style")
nodes = importlib.import_module(PKG + ".nodes_studio")


def _tags(text):
    return [t.strip() for t in str(text or "").split(",") if t.strip()]


def test_manual_extra_body_goes_through_repair():
    items = [{"en": "long hair", "zh": "长发", "slot": "appearance", "w": 1}]
    res = manual.compose_manual(items, level="sfw", extra_body="long hair")
    assert res["tags"].count("long hair") == 1, res["text"]

    high = next((t for t in ("sex", "nude", "cum", "penis", "topless")
                 if rules.tag_level(t) > 0), None)
    assert high, "找不到可用于测试的高档 tag"
    res2 = manual.compose_manual(items, level="sfw", extra_body=high)
    assert high not in res2["tags"], res2["text"]
    assert res2["report_detail"]["real_level"] <= 0, res2["report_detail"]["real_level"]
    print("1 extra_body repair: OK ->", res["text"], "| blocked", high)


def test_selector_filters_manual_picks_by_max_level():
    all_clothes = catalog.items(cat="clothing", limit=500, level_max=None)["items"]
    high = next((it for it in all_clothes if int(it["level"] or 0) >= 2), None)
    assert high, "找不到高档服装 item"
    sel = nodes.AnimaPromptStudioSelector()
    text, count, report = sel.select(
        high["cat"], picked_json=json.dumps([{"id": high["id"]}]),
        random_count=0, max_level="sfw")
    assert count == 0 and text == "", (text, count, report)
    print("2 selector max_level: OK -> blocked", high["id"], high["level"])


def test_random_keeps_extra_text():
    studio = {"mode": "random", "items": []}
    res = manual.compose(studio, {
        "seed": 42, "nsfw_level": "sfw", "weights_json": "",
        "tag_cap": "自动", "extra_body": "",
    })
    studio["extra_text"] = "rain, street"
    res2 = manual.compose(studio, {
        "seed": 42, "nsfw_level": "sfw", "weights_json": "",
        "tag_cap": "自动", "extra_body": "",
    })
    assert "rain" in res2["tags"] and "street" in res2["tags"], res2["text"]
    res3 = manual.compose(studio, {
        "seed": 42, "nsfw_level": "sfw", "weights_json": "",
        "tag_cap": "自动", "extra_body": "rain",
    })
    assert res3["tags"].count("rain") == 1, res3["text"]
    print("3 random extra_text: OK ->", "rain, street")


def test_hybrid_negative_seed_breaks_cache():
    kwargs = dict(seed=-1, mode="hybrid", studio_json="{}", nsfw_level="sfw")
    a = nodes.AnimaPromptStudio.IS_CHANGED(**kwargs)
    b = nodes.AnimaPromptStudio.IS_CHANGED(**kwargs)
    assert a != b, (a, b)
    print("4 hybrid seed=-1 fingerprint: OK")


def test_clothing_levels_are_calibrated():
    all_clothes = catalog.items(cat="clothing", limit=500, level_max=None)["items"]
    bad = []
    for it in all_clothes:
        actual = max([int(it["level"] or 0)] + [
            rules.tag_level(t.strip()) for t in str(it["en"]).split(",") if t.strip()])
        if actual != int(it["level"] or 0):
            bad.append((it["id"], it["level"], actual))
    assert not bad, bad[:5]
    safe = catalog.items(cat="clothing", limit=500, level_max=0)["items"]
    assert all(int(it["level"] or 0) == 0 for it in safe)
    print("5 clothing levels: OK ->", len(all_clothes), "items; sfw", len(safe))


def test_negative_strips_weights_before_matching():
    assert negative.build_negative("(night:1.2)", level=0) == \
        negative.build_negative("night", level=0)
    out = negative.build_negative("(lowres:1.2)", level=0)
    assert "lowres" not in _tags(out), out
    print("6 negative weighted matching: OK")


def test_outfit_summary_does_not_nameerror():
    summary = style.summary()
    assert summary["color_targets"], summary
    assert summary["matrix_colors"] > 0
    print("7 outfit summary: OK ->", summary["color_targets"])


def test_catalog_drops_empty_en():
    assert catalog._item("x", "", "只有中文") is None
    backgrounds = [it for it in catalog.ensure()["items"] if it["cat"] == "background"]
    assert backgrounds and all(it["en"].strip() for it in backgrounds)
    print("8 empty en: OK ->", len(backgrounds), "backgrounds")


def main():
    test_manual_extra_body_goes_through_repair()
    test_selector_filters_manual_picks_by_max_level()
    test_random_keeps_extra_text()
    test_hybrid_negative_seed_breaks_cache()
    test_clothing_levels_are_calibrated()
    test_negative_strips_weights_before_matching()
    test_outfit_summary_does_not_nameerror()
    test_catalog_drops_empty_en()
    print("all bugfix tests passed")


if __name__ == "__main__":
    main()
