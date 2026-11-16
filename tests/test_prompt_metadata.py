# -*- coding: utf-8 -*-
"""V6 正文 -> 真正提示词 -> PNG 元数据 的回归测试。

运行：
    python tests/test_prompt_metadata.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import anima_v4_pngmeta as PM  # noqa: E402
import prompt_decouple as PD  # noqa: E402

RAW = (
    "1girl, long hair, red eyes, "
    "she stands in a door frame with both forearms pressed against the frame, "
    "masterpiece, best quality"
)


def test_decouple_mixed_caption():
    out = PD.decouple(RAW)
    prompt = out["prompt"]
    assert "1girl" in prompt, prompt
    assert "long hair" in prompt, prompt
    assert "doorway" in prompt or "door frame" in prompt, prompt
    assert "she stands in a door frame" not in prompt, prompt
    assert out["prompt_nl"].startswith("An anime illustration"), out["prompt_nl"]
    assert out["negative"]
    print("decouple: OK ->", prompt)


def test_convert_prompt_fallback_shape():
    out = PM.convert_prompt("")
    assert out["status"] == "empty"
    assert out["prompt"] == ""
    assert out["error"] == ""
    print("empty conversion: OK")


def test_metadata_default_conversion_and_raw_preserved():
    extra = {}
    api = {"1": {"class_type": "AnimaPromptStudio", "inputs": {}}}
    st = PM.inject_metadata(extra, api, RAW, self_ids={"1"}, version="test")

    meta = st["meta"]
    assert meta["positive"] != RAW
    assert "1girl" in meta["positive"]
    assert "she stands in a door frame" not in meta["positive"]
    assert meta["positive_raw"] == RAW
    assert meta["conversion"]["status"] == "ok"
    assert meta["prompt_nl"].startswith("An anime illustration")
    assert meta["negative"]
    assert extra[PM.TEXT_KEY] is meta
    assert extra[PM.LEGACY_TEXT_KEY] is meta
    assert api["1"]["inputs"][PM.INJECT_KEY] == json.dumps(meta, ensure_ascii=False)
    print("metadata: OK ->", meta["positive"])


def test_workflow_seed_for_studio_node():
    workflow = {
        "nodes": [
            {
                "id": 1, "type": "AnimaPromptStudio",
                "outputs": [{"name": "text", "links": [1]}],
            },
            {
                "id": 2, "type": "CR Text",
                "inputs": [{"name": "text", "link": 1}],
                "widgets_values": [""],
                "widgets_values_named": {"text": ""},
            },
        ],
        "links": [[1, 1, 0, 2, 0]],
    }
    extra = {"workflow": workflow}
    api = {"1": {"class_type": "AnimaPromptStudio", "inputs": {}}}
    st = PM.inject_metadata(extra, api, RAW, self_ids={"1"}, version="test")
    meta = st["meta"]
    assert meta["workflow_ok"] is True, st
    assert "1girl" in meta["positive_full"]
    assert "1girl" in workflow["nodes"][1]["widgets_values"][0]
    print("studio workflow seed: OK ->", meta["workflow_ok"])


if __name__ == "__main__":
    test_decouple_mixed_caption()
    test_convert_prompt_fallback_shape()
    test_metadata_default_conversion_and_raw_preserved()
    test_workflow_seed_for_studio_node()
    print("all prompt metadata tests passed")
