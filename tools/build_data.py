# -*- coding: utf-8 -*-
"""把 Anima-Tools 的 JS 数据模块转成本插件可直接读取的 JSON。

用法：
    python tools/build_data.py [--tools-dir <path>]

只在**开发期**运行；插件运行时不依赖本脚本。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_TOOLS = os.path.join(
    os.path.dirname(ROOT), "tmp", "refs", "Comfyui-Anima-Tools", "js")

# (源文件, 目标文件名, 期望顶层类型)
JS_FILES = [
    ("data.js", "artists.json", list),
    ("character_data.js", "characters_lite.json", list),
    ("clothing_data.js", "clothing.json", list),
    ("pose_data.js", "poses.json", list),
    ("background_data.js", "backgrounds.json", list),
    ("composition_style_data.js", "composition_style.json", list),
    ("qianteng_data.js", "qianteng.json", list),
    ("raven_data.js", "raven.json", list),
]
JSON_FILES = [
    ("character_official_data.json", "character_official.json"),
    ("danbooru_attire_data.json", "danbooru_attire.json"),
]


def parse_js_array(text: str):
    """从 `const xxx = [ ... ];` 里取出数组并 JSON 解析。"""
    m = re.search(r"const\s+\w+\s*=\s*", text)
    if not m:
        raise ValueError("找不到 const 赋值")
    body = text[m.end():].lstrip()
    if not body.startswith("["):
        raise ValueError("赋值不是数组")
    # 只截取**第一个配平的数组**：部分源文件（data.js）在数组后面还有
    # 别的 const 定义 / 导出语句，直接 rstrip 后 json.loads 会报 Extra data。
    depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(body):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return json.loads(body[:i + 1])
    raise ValueError("数组括号没有配平")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools-dir", default=DEFAULT_TOOLS)
    args = ap.parse_args()

    out_dir = os.path.join(ROOT, "data", "tools")
    os.makedirs(out_dir, exist_ok=True)

    counts = {}
    for src, dst, expect in JS_FILES:
        path = os.path.join(args.tools_dir, src)
        if not os.path.isfile(path):
            print(f"[skip] 缺少 {path}")
            continue
        with open(path, "r", encoding="utf-8") as fh:
            data = parse_js_array(fh.read())
        if not isinstance(data, expect):
            raise TypeError(f"{src} 顶层不是 {expect}")
        with open(os.path.join(out_dir, dst), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        counts[dst] = len(data)
        print(f"[ok] {src} -> {dst} ({len(data)})")

    for src, dst in JSON_FILES:
        path = os.path.join(args.tools_dir, src)
        if not os.path.isfile(path):
            print(f"[skip] 缺少 {path}")
            continue
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        with open(os.path.join(out_dir, dst), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        counts[dst] = len(data)
        print(f"[ok] {src} -> {dst} ({len(data)})")

    with open(os.path.join(out_dir, "_counts.json"), "w", encoding="utf-8") as fh:
        json.dump(counts, fh, ensure_ascii=False, indent=2)
    print("总计：", sum(counts.values()))


if __name__ == "__main__":
    sys.exit(main())
