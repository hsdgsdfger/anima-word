# 第三方来源与许可声明

本插件 `anima-word` 不是从零凭空生成的工具。它的 V6 底座、
词库、场景库、服装库、角色缩略图和面板，来自下面两个上游项目；`Anima-Tools`
 的数据被转换成 JSON，Danbooru 节点也被移植进来。这里把来源、许可和改动范围
写清楚，方便分发、二次开发和权利人核对。

## 1. Comfyui-Anima-Wardrobe-V6

- 仓库：https://github.com/lingdongbudong/Comfyui-Anima-Wardrobe-V6
- 作者：灵冻不冻
- 许可：GPL-3.0（仓库根目录 `LICENSE`）
- 本插件中来自 V6 的部分：
  - Python 引擎：`anima_v4_rules.py`、`anima_v4_nsfw.py`、`anima_v4_store.py`、
    `anima_v4_outfit_style.py`、`anima_v4_overrides.py`、`anima_v4_link.py`、
    `anima_v4_pngmeta.py`
  - 节点与路由：`nodes_v6.py`（原 `nodes.py`）、`routes_v6.py`（原 `__init__.py`）
  - 面板：`js/v6_panel.js`（原 `js/anima_wardrobe_v4_studio.js`，仅改扩展名、
    节点类型与路由前缀）
  - 数据：`presets/` 全部 JSON、`presets/thumbs/` 2432 张角色缩略图
- 改动：包名、节点类名前缀改为 `AnimaPromptStudio*`，HTTP 前缀改为
  `/anima-prompt-studio`；主节点在 V6 控件末尾追加 `mode`、`studio_json`、
  `manual_text`；V6 面板的节点类型与 API 前缀改为新插件。
- V6 的 `LICENSE` 末尾还有一段“附加说明”，已随 `LICENSE` 原样保留。角色名、
  作品名等知识产权归各自权利人；角色缩略图为 V6 作者本机出图产物，本插件只
  用于面板内的角色识别对照。

## 2. Comfyui-Anima-Tools

- 仓库：https://github.com/nregret/Comfyui-Anima-Tools
- 作者：nregret
- 许可：MIT（README 第 256 行“本项目以 MIT 协议开源”，仓库未单独放 LICENSE 文件）
- 本插件中来自 Tools 的部分：
  - 数据：`data/tools/*.json`，由 `tools/build_data.py` 从 Tools 的 JS 数据转换
    （画师 42,197；角色 8,000；服装 430；姿势 297；背景 1,087；构图风格 64；
    千藤 125；渡鸦 6,570；Danbooru attire 8）
  - 节点：`nodes_danbooru.py`（原 `nodes_danbooru.py`，类名改为
    `AnimaPromptStudioDanbooru`，分类改为 `AnimaPromptStudio`）
- 改动：路径、类名、分类名；数据统一转换成 JSON，并做分页/去重/中文名补全。
- MIT 许可文本（标准 MIT License）：

```
MIT License

Copyright (c) 2026 nregret

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 3. PromptForge / 提示词生成器 v3.0

用户提供的两个压缩包只作为**产品思路参考**（分类侧栏、手选托盘、预览、
预设、AI 占位等交互），没有复制其中的代码或数据。它们各自的许可与数据来源
以原项目为准，本插件不包含其素材。

## 4. 本插件的许可

本插件整体按 GPL-3.0 发布，全文见仓库根目录 `LICENSE`。因为包含 V6 的
GPL-3.0 代码，不能改为更宽松的许可；如果只使用 Tools 的 MIT 部分，仍应保留
上面的 MIT 声明。

## 5. 免责与使用边界

- 本插件按“原样”提供，不附带任何明示或暗示的担保。
- 成人向词库、场景和服装只用于虚构角色的提示词创作；所有角色视为 18 岁以上
  虚构人物。禁止用于真实人物、未成年人、非自愿或暴力伤害内容。
- 角色名、作品名、画师名及相关设定，知识产权归各自权利人；本插件只在提示词
  层面做标签检索与描述。
- 角色缩略图、服装/姿势/背景预览图来自 V6 或 Tools 的公开数据；若权利人提出
  移除要求，应删除对应文件并重新生成目录缓存。
