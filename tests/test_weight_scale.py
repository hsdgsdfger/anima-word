# -*- coding: utf-8 -*-
"""权重 0–5 语义回归：0 不出现，5 必现，互斥字段只保留一个必现。

运行：
    python tests/test_weight_scale.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import importlib  # noqa: E402
import smoke_backend  # noqa: E402

smoke_backend.load_plugin()
R = importlib.import_module("anima_prompt_studio.anima_v4_rules")


def test_weight_range():
    assert R.WEIGHT_MIN == 0.0
    assert R.WEIGHT_MAX == 5.0
    assert R._as_weight(5) == 5.0
    assert R._as_weight(0) == 0.0
    assert R._as_weight(9) == 5.0
    print("weight range: OK", R.WEIGHT_MIN, R.WEIGHT_MAX)


def test_forced_option_only_five():
    w = R.parse_weights({
        "options": {"hair_len": {"long hair": 5, "short hair": 4}},
    })
    pool = [("a", "long hair"), ("b", "short hair")]
    forced = R.forced_option_pool(pool, "hair_len", w)
    assert [x[1] for x in forced] == ["long hair"], forced
    print("forced option: OK", forced)


def test_mutex_keeps_last_five():
    w = {"options": {"hair_len": {"a": 5, "b": 5}}}
    notes = R.enforce_option_mutex(w)
    assert notes, notes
    assert w["options"]["hair_len"]["a"] == 1.0
    assert w["options"]["hair_len"]["b"] == 5.0
    print("mutex: OK", notes[0])


def test_dump_keeps_five():
    w = {"sections": {"hair": 5}, "fields": {"hair_len": 5},
         "options": {"hair_len": {"long hair": 5}}}
    text = R.dump_weights(w)
    assert "5" in text, text
    print("dump: OK ->", text.replace("\n", " ")[:120])


if __name__ == "__main__":
    test_weight_range()
    test_forced_option_only_five()
    test_mutex_keeps_last_five()
    test_dump_keeps_five()
    print("all weight scale tests passed")
