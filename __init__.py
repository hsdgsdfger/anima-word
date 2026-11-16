# -*- coding: utf-8 -*-
"""anima-word

以 Comfyui-Anima-Wardrobe-V6 为底座，合并 Comfyui-Anima-Tools 的选择器 /
多框提示词 / LoRA 能力，并新增：

  · 自由选择（manual）与混合（hybrid）出词
  · 统一目录：V6 词库 + V6 角色/场景/服装 + Tools 画师/角色/服装/姿势/背景
    + 社区 Tag 库 + 我的 Tag
  · 可拖拽排序的多 LoRA 加载器（数组顺序 = 应用顺序）
  · AI provider 接口（默认关闭，不联网）

节点与 V6 的类名**完全不同**，两个插件可以并存；新工作流请用本插件节点。
"""
from __future__ import annotations

__version__ = "1.0.3"

from .nodes_v6 import (
    AnimaV4PromptAssemble as _V6Assemble,
    AnimaV4PromptCheck as _V6Check,
    AnimaV4PromptGrader as _V6Grader,
    AnimaV4RandomPrompt as _V6Random,
)
from .nodes_studio import (
    AnimaPromptStudio,
    AnimaPromptStudioBoxes,
    AnimaPromptStudioBoxesEncode,
    AnimaPromptStudioEncode,
    AnimaPromptStudioSelector,
)
from .nodes_lora import AnimaLoraStack
from .nodes_danbooru import AnimaPromptStudioDanbooru

NODE_CLASS_MAPPINGS = {
    # 主节点
    "AnimaPromptStudio": AnimaPromptStudio,
    # 纯随机 / 分级 / 拼接 / 修复（V6 能力的独立节点）
    "AnimaPromptStudioRandom": _V6Random,
    "AnimaPromptStudioGrader": _V6Grader,
    "AnimaPromptStudioMerge": _V6Assemble,
    "AnimaPromptStudioRepair": _V6Check,
    # 编码 / 多框 / 选择器 / LoRA
    "AnimaPromptStudioEncode": AnimaPromptStudioEncode,
    "AnimaPromptStudioBoxes": AnimaPromptStudioBoxes,
    "AnimaPromptStudioBoxesEncode": AnimaPromptStudioBoxesEncode,
    "AnimaPromptStudioSelector": AnimaPromptStudioSelector,
    "AnimaLoraStack": AnimaLoraStack,
    "AnimaPromptStudioDanbooru": AnimaPromptStudioDanbooru,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaPromptStudio": "anima-word · 提示词工坊（自由选择 + V6）",
    "AnimaPromptStudioRandom": "anima-word · 提示词随机生成（V6 引擎）",
    "AnimaPromptStudioGrader": "anima-word · 提示词分级审查",
    "AnimaPromptStudioMerge": "anima-word · 提示词拼接台",
    "AnimaPromptStudioRepair": "anima-word · 提示词检查与修复",
    "AnimaPromptStudioEncode": "anima-word · 提示词编码（CLIP）",
    "AnimaPromptStudioBoxes": "anima-word · 多提示词框",
    "AnimaPromptStudioBoxesEncode": "anima-word · 多提示词框编码（CLIP）",
    "AnimaPromptStudioSelector": "anima-word · 标签选择器",
    "AnimaLoraStack": "anima-word · 多 LoRA 加载器（可排序）",
    "AnimaPromptStudioDanbooru": "anima-word · Danbooru 随机参考图（联网·可选）",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

# V6 路由在 import 时自行注册；这里只注册新增路由。
try:
    from . import routes_v6  # noqa: F401  (import 即注册 V6 路由)
except Exception as exc:  # pragma: no cover
    print(f"[anima-word] V6 路由导入失败（不影响节点使用）: {exc}")

try:
    from . import routes_studio
    routes_studio.register()
except Exception as exc:  # pragma: no cover
    print(f"[anima-word] 新路由注册失败（不影响节点使用）: {exc}")
