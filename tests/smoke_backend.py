# -*- coding: utf-8 -*-
"""后端冒烟测试：不依赖 ComfyUI，直接按包加载插件。

运行：
    python tests/smoke_backend.py
"""
import importlib.util
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PKG = "anima_prompt_studio"


def load_plugin():
    init = os.path.join(ROOT, "__init__.py")
    spec = importlib.util.spec_from_file_location(
        PKG, init, submodule_search_locations=[ROOT])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[PKG] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    print("== load ==")
    mod = load_plugin()
    print("version:", mod.__version__)
    print("nodes:", len(mod.NODE_CLASS_MAPPINGS))
    for k, v in mod.NODE_CLASS_MAPPINGS.items():
        print("  ", k, "->", v.__name__)
    assert "AnimaPromptStudio" in mod.NODE_CLASS_MAPPINGS
    assert "AnimaLoraStack" in mod.NODE_CLASS_MAPPINGS
    assert "AnimaPromptStudioDanbooru" in mod.NODE_CLASS_MAPPINGS

    import importlib
    catalog = importlib.import_module(PKG + ".catalog")
    manual = importlib.import_module(PKG + ".manual")
    negative = importlib.import_module(PKG + ".negative")
    ai = importlib.import_module(PKG + ".ai_bridge")

    print("== catalog ==")
    meta = catalog.meta()
    print("total:", meta["total"], "cats:", len(meta["counts"]))
    for g in meta["groups"]:
        print(" ", g["title"], sum(c["count"] for c in g["cats"]))
    for cat in ("v6:hair", "v6char", "artist", "character", "clothing",
                "pose", "background", "scene_sfw", "my"):
        res = catalog.items(cat=cat, page=1, limit=3)
        print(f"  {cat}: total={res['total']} sample={res['items'][:1]}")
    assert meta["total"] > 60000, meta["total"]

    print("== manual compose ==")
    items = [
        {"id": "v6:hair:long hair", "cat": "v6:hair", "en": "long hair",
         "zh": "长发", "slot": "appearance", "w": 1.2},
        {"id": "v6:hair:silver hair", "cat": "v6:hair", "en": "silver hair",
         "zh": "银发", "slot": "appearance", "w": 1.0},
        {"id": "v6:camera:from above", "cat": "v6:camera", "en": "from above",
         "zh": "俯视", "slot": "camera", "w": 1.0},
        {"id": "v6:lighting:cinematic lighting", "cat": "v6:lighting",
         "en": "cinematic lighting", "zh": "电影光", "slot": "lighting", "w": 1.0},
    ]
    studio = {"mode": "manual", "items": items, "order": "custom",
              "negative_preset": "standard"}
    res = manual.compose(studio, {"nsfw_level": "sfw", "extra_body": "solo"})
    print("text:", res["text"])
    print("level:", res["level_label"], "counts:", res["counts"])
    print("negative:", res["negative"][:200])
    assert "long hair" in res["text"]
    assert res["negative"]
    assert res["counts"]["total"] >= 4
    assert "F1" not in res["report"] and "F2" not in res["report"]
    assert "不检查标签数量" in res["report"]

    print("== hybrid compose ==")
    res2 = manual.compose({"mode": "hybrid", "items": items[:1], "order": "custom"},
                          {"nsfw_level": "sfw", "seed": 42})
    print("text:", res2["text"][:300])
    print("counts:", res2["counts"])
    assert res2["counts"]["drawn"] > 0
    assert "(long hair:1.2)" in res2["text"], res2["text"]

    print("== catalog source filter ==")
    builtin = catalog.items(src="builtin", page=1, limit=3)
    print("builtin:", builtin["total"], builtin["items"][:1])
    assert builtin["total"] == 8, builtin["total"]

    print("== catalog scene random ==")
    scene_pick = catalog.sample("v6:scene", 5, seed=7)
    print("scene sample:", [it["en"] for it in scene_pick])
    assert len(scene_pick) == 5
    assert all((it.get("extra") or {}).get("section") == "scene"
               for it in scene_pick)

    print("== selector random ==")
    selector = mod.NODE_CLASS_MAPPINGS["AnimaPromptStudioSelector"]()
    picked = selector.select("artist", "[]", 42, 3)
    print("selector:", picked[0][:200], "count:", picked[1])
    assert picked[1] >= 3
    assert len(catalog.sample("artist", 3, seed=1)) == 3

    print("== random compose ==")
    res3 = manual.compose({"mode": "random"}, {"nsfw_level": "sfw", "seed": 123})
    print("text:", res3["text"][:200])
    assert res3["text"]

    print("== negative ==")
    print(negative.build_negative("1girl, solo, nude, outdoors", 2)[:200])

    print("== ai ==")
    st = ai.status()
    print(json.dumps(st, ensure_ascii=False)[:300])
    assert st["enabled"] is False
    try:
        ai.enhance({"task": "enhance"})
    except ai.AIUnavailable as exc:
        print("ai not enabled ok:", exc)

    print("\nALL OK")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
