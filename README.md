# Comfyui-Anima-Prompt-Studio · Anima 提示词工坊

一个**独立、自包含**的 ComfyUI 自定义节点包：把
[Comfyui-Anima-Wardrobe-V6](https://github.com/lingdongbudong/Comfyui-Anima-Wardrobe-V6)
的随机提示词引擎，和
[Comfyui-Anima-Tools](https://github.com/nregret/Comfyui-Anima-Tools)
的素材库 / 多提示词框 / 多 LoRA 加载器合成一套面板。

- 版本：`1.0.2`（V6 引擎内部版本 `7.0.0`）
- 许可：GPL-3.0（因为内嵌 V6；详见 `LICENSE`、`THIRD_PARTY_NOTICES.md`）
- 依赖：无第三方 Python 依赖；只要 ComfyUI 自带的 Python 环境
- 真机验证：ComfyUI `0.45.3` / Python `3.13.12` / 前端 `1.58.5`

> **1.0.2 更新（2026-11）**：目录页新增「🎲 随机一条 / 随机场景」按钮。当前分类
> 是场景相关分类时自动变成「🎲 随机场景」，从整个分类随机抽取，不受首屏 60 条
> 限制；支持搜索、来源、档位过滤，抽到的场景会直接进手选托盘。后端新增
> `GET /anima-prompt-studio/catalog/random`。
>
> **1.0.1 更新（2026-11）**：修复混合模式手选权重丢失、手选角色被随机角色/官方
> 外貌覆盖、选择器随机模式崩溃、目录来源筛选失效、按槽位排序时托盘移动无效、
> LoRA 同名文件替换后缓存不刷新；关闭工坊面板时会立即保存，不再依赖 300ms
> debounce。
>
> **它不需要你先安装 V6 或 Anima-Tools。** V6 的 Python 引擎、presets、
> 2432 张角色缩略图和整套 V6 面板都已内嵌。新插件使用全新的节点类名和
> `/anima-prompt-studio` 路由前缀，所以可以和原来的 V6 / Tools 同时安装，
> 不会抢路由、也不会互相覆盖节点。

---

## 1. 它解决什么问题

V6 很强，但它是“随机抽一整段”；Anima-Tools 的素材很多，但它的多 LoRA
加载器只能按“添加顺序”应用，前端没有拖拽排序。这个插件在 V6 的底座上补了
三件事：

1. **提示词可以自由选择**：不再只能随机。目录里 6.2 万条标签可以搜索、
   分页、按分类挑；挑中的条目进“手选托盘”，可调权重、开关、拖拽排序。
2. **三种出词模式**：`manual`（只出手选）/ `hybrid`（手选打底，V6 随机补
   未覆盖的段）/ `random`（完全走 V6 引擎）。
3. **LoRA 顺序真的可调**：`AnimaLoraStack` 的 `lora_list_json` 是**有序数组**，
   数组下标就是加载顺序；面板支持拖拽、上移/下移、复制、启用开关、
   model/clip 双强度、触发词、命名堆栈保存/加载/导入导出。

另外把 Anima-Tools 的画师 / 角色 / 服装 / 姿势 / 背景 / 社区 Tag 库并进同一
张目录；AI 功能按用户要求**暂不实现**，只留下 provider 接口和请求/响应契约。

---

## 2. 功能总览

| 能力 | 来源 | 在本插件里的形态 |
|---|---|---|
| V6 随机引擎（15 段 / 57 字段 / 1134 选项） | V6 | 主节点 `random` 模式 / `AnimaPromptStudioRandom` |
| V6 场景 524 条、服装库 135 套、角色 2432 个 | V6 | 目录分类 + 手选 + V6 面板 |
| V6 五级档位、三层权重、成品自检、自动修复 | V6 | 主节点控件 + 报告输出 |
| V6 8 页签面板 | V6 | `js/v6_panel.js`，节点上“⚙ 打开随机面板” |
| 画师 42,197 / 角色 8,000 / 服装 430 / 姿势 297 / 背景 1,087 | Tools | 统一目录 `artist` / `character` / `clothing` / `pose` / `background` |
| 构图风格 64 / 千藤 125 / 渡鸦 6,570 / Danbooru attire 8 | Tools | 社区 Tag 库分类 |
| 多提示词框（每框开关 / 排序 / 去重 / 截断） | Tools | `AnimaPromptStudioBoxes` + `BoxesEncode` |
| 分类选择器（画师/角色/服装/姿势/背景…） | Tools | `AnimaPromptStudioSelector`（通用选择器，12 类） |
| 多 LoRA 加载器 | Tools 思路 | `AnimaLoraStack`，**有序数组 + 拖拽排序** |
| 随机 Danbooru 参考图 | Tools | `AnimaPromptStudioDanbooru`（可选、联网） |
| 手选托盘 / 权重 / 开关 / 拖拽 | 新增 | 主工坊面板右侧 |
| 负面词基线 / 档位压制 / 冲突对 | 新增 | `negative.py` + 面板“负面词”设置 |
| 我的 Tag / 收藏 / 最近使用 | 新增 | 面板页签 + 用户目录 JSON |
| 预设 / 历史 / 导入导出 | 新增 | 面板页签（localStorage） |
| AI provider 接口 | 预留 | `ai_bridge.py`，默认关闭，`/ai/enhance` 返回 501 |

统一目录当前规模：**62,585 条 / 31 个分类**。分组：

| 分组 | 条数 |
|---|---:|
| 基础词库 | 971 |
| 素材库 | 54,549 |
| 场景与构图 | 524 |
| 社区 Tag 库 | 6,386 |
| 成人向（受档位闸门约束） | 155 |

> 数字来自 `catalog.meta()`。目录在首次请求时建索引，之后走内存缓存；
> 单类分页返回，不会一次把 4 万条画师塞给浏览器。

---

## 3. 安装

### 3.1 手动安装（推荐）

把整个 `Comfyui-Anima-Prompt-Studio` 文件夹放进：

```text
<你的 ComfyUI>/custom_nodes/Comfyui-Anima-Prompt-Studio
```

目录里应该能直接看到 `__init__.py`、`nodes_studio.py`、`js/`、`presets/`。
然后重启 ComfyUI。启动日志里应出现：

```text
[AnimaPromptStudio] v7.0.0 V6 路由已注册: ...
[AnimaPromptStudio] 新路由已注册: catalog / compose / studio / loras / ai
```

浏览器打开 ComfyUI，右键画布 → `AnimaPromptStudio` 分类下能看到 11 个节点。

> 不需要 `pip install`。V6 引擎、Tools 数据、缩略图都已放在插件目录里。
> 如果你的 ComfyUI 是便携版，路径通常是
> `<ComfyUI_windows_portable>/ComfyUI/custom_nodes/`。

### 3.2 更新

用新版本覆盖插件目录即可。**用户数据不在插件目录里**，不会被覆盖：

```text
<ComfyUI>/user/anima_prompt_studio/
├── studio_favorites.json
├── my_tags.json
├── lora_meta.json
├── lora_stacks.json
└── ai_providers.json
```

`presets/` 是内置词库，升级时会被新版本替换；自己改过的 presets 请另存。

### 3.3 卸载

删除 `custom_nodes/Comfyui-Anima-Prompt-Studio`，重启。用户数据目录可保留，
也可以手动删除。

### 3.4 LoRA 放哪里

`AnimaLoraStack` 读取 ComfyUI 的 `models/loras`（`folder_paths` 注册的所有
LoRA 路径）。把 `.safetensors` 放进去，重启或刷新节点后，面板“本地 LoRA”
列表会出现。测试机识别到 21 个 LoRA。

---

## 4. 快速开始

### 4.1 最常用的工作流

```text
AnimaPromptStudio
  ├─ text ───────────────► CLIP Text Encode（正向）──► KSampler positive
  ├─ negative ───────────► CLIP Text Encode（负向）──► KSampler negative
  ├─ lora_json ──────────► AnimaLoraStack（右键 lora_list_json → 转输入）
  └─ report / level / cn_summary ──► 可选：Show Text / 调试
```

`AnimaPromptStudio` 的 6 个输出：

| 输出 | 类型 | 说明 |
|---|---|---|
| `text` | STRING | 最终正向提示词 |
| `report` | STRING | 体检报告（手选模式为专用报告） |
| `level` | STRING | 档位标签，如 `0 · 全年龄` |
| `cn_summary` | STRING | 中文摘要，方便核对选了什么 |
| `negative` | STRING | 负面提示词（按档位/冲突对生成） |
| `lora_json` | STRING | 工坊里配好的**有序** LoRA 数组，接 `AnimaLoraStack` |

主节点在 V6 原有控件**末尾**追加了三个 optional 控件，V6 控件顺序不变：

- `mode`：`manual` / `hybrid` / `random`
- `studio_json`：手选状态（面板读写，一般不用手改）
- `manual_text`：临时手写补充，按逗号拼进正文

### 4.2 打开工坊面板

选中 `AnimaPromptStudio` 节点，点节点上的 **“🎨 打开提示词工坊”**。面板分
三栏：

- 左栏：分类侧栏（全部 / 我的收藏 / 最近使用 / 基础词库 / 素材库 / 场景与
  构图 / 社区 Tag 库 / 成人向），支持搜索。
- 中栏：卡片目录（缩略图、中文名、英文 tag、槽位、档位、来源），点卡片即
  加入/移出托盘；星标收藏。
- 右栏：手选托盘 + 预览 + 模式 / 档位 / 排序 / 质量前缀 / 额外补充 / 负面词。

子页签：`自由选择`、`LoRA`、`我的 Tag`、`预设 / 历史`、`AI（预留）`。

### 4.3 三种模式怎么选

| 模式 | 行为 | 适合 |
|---|---|---|
| `manual` | 只输出勾选条目；`quality_prefix` 可选；不检查标签数量/质量词 | 你已经想好要什么，只要一个干净的拼接器 |
| `hybrid` | 手选条目先占位；V6 随机补未覆盖的段，直到 `tag_cap` | 想保留几个关键 tag，其余交给随机 |
| `random` | 完全走 V6 引擎，和 V6 节点逐字节一致 | 抽卡、找灵感 |

手选模式的报告是**单独实现**的：不会再把“标签太少（F1）”“含质量词（F2）”
当成致命项吓人，只保留互斥、超档、格式等真正需要看的检查项。

### 4.4 手选状态长什么样

`studio_json` 随工作流保存，结构：

```json
{
  "version": 1,
  "mode": "manual",
  "items": [
    {"id": "v6:hair:long hair", "cat": "v6:hair", "en": "long hair",
     "zh": "长发", "slot": "hair", "w": 1.2, "on": true, "src": "v6"}
  ],
  "order": "slot",
  "quality_prefix": "masterpiece, best quality",
  "extra_text": "",
  "negative_preset": "standard",
  "negative_extra": "",
  "lora": [],
  "ui": {}
}
```

- `order = "slot"`：按 V6 槽位顺序（观感更接近随机引擎）
- `order = "custom"`：按手选托盘里的拖拽顺序
- `items[].w`：权重，`1.0` 不写括号，`1.2` 输出 `(long hair:1.2)`
- `on: false`：条目留在托盘但不参与出词

---

## 5. 节点清单（11 个）

| 节点类名 | 显示名 | 作用 |
|---|---|---|
| `AnimaPromptStudio` | Anima 提示词工坊 | 主节点，三模式 + 6 输出 |
| `AnimaPromptStudioRandom` | Anima 随机提示词（V6） | 纯 V6 随机节点，保留 V6 全部控件 |
| `AnimaPromptStudioGrader` | Anima 提示词体检 | V6 `PromptGrader` |
| `AnimaPromptStudioMerge` | Anima 提示词拼装 | V6 `PromptAssemble` |
| `AnimaPromptStudioRepair` | Anima 提示词修复 | V6 `PromptCheck` |
| `AnimaPromptStudioEncode` | Anima CLIP 编码 | 正/负提示词一次编码成 CONDITIONING |
| `AnimaPromptStudioBoxes` | Anima 多提示词框 | 多框开关/排序/去重/截断 |
| `AnimaPromptStudioBoxesEncode` | Anima 多框编码 | 多框 + CLIP 一步到位 |
| `AnimaPromptStudioSelector` | Anima 分类选择器 | 12 类素材的选择器，写入 `text` |
| `AnimaLoraStack` | Anima 多 LoRA 加载器（可排序） | 有序数组逐项加载 |
| `AnimaPromptStudioDanbooru` | Anima Danbooru 随机参考图（联网·可选） | 随机图 + 分组标签，来自 Tools |

---

## 6. LoRA 顺序：这次真的能调

### 6.1 在工坊里配

1. 打开主节点面板 → `LoRA` 页签。
2. 左侧“本地 LoRA”点 `＋` 加入右侧“应用顺序”。
3. 右侧每一项：
   - `⋮⋮` 拖拽手柄：直接拖动排序；
   - `↑` / `↓`：上移/下移；
   - `⧉`：复制；
   - `✕`：移除；
   - `启用`：关掉的不加载；
   - `model` / `clip`：两个强度分开；
   - `触发词`：可填多个，用逗号分隔。
4. 数字 `1, 2, 3…` 就是实际加载顺序。
5. 点“写回节点”，面板会把 `lora` 数组写进 `studio_json`；主节点的
   `lora_json` 输出就是这份**有序**数组。

### 6.2 接到 `AnimaLoraStack`

1. 把 `AnimaPromptStudio.lora_json` 连到 `AnimaLoraStack` 的 `lora_list_json`。
2. 如果 `lora_list_json` 是必填输入，右键该输入 → `Convert to input`（转成
   输入），再连线。
3. `AnimaLoraStack` 逐项调用 `load_lora_for_models`，数组下标即顺序：

```json
[
  {"name": "style-a.safetensors", "strength_model": 0.8, "strength_clip": 0.8,
   "on": true, "trigger": "style a"},
  {"name": "character-b.safetensors", "strength_model": 1.0, "strength_clip": 1.0,
   "on": true, "trigger": "character b"}
]
```

4. 节点有 `trigger_text` 输出，把触发词拼成一段，可接到正向提示词后面。
5. 面板支持命名堆栈（保存/加载/删除/导入/导出 JSON）；堆栈存在
   `user/anima_prompt_studio/lora_stacks.json`。

> 已知限制：没有做 Civitai 在线检索/下载（Anima-Tools 的 LoRA 管理器有这
> 一块）。当前只管理本地 `models/loras`；如果你需要在线发现，可以在这个
> `AnimaLoraStack` 旁边加一个独立下载节点，不必改排序核心。

---

## 7. 我的 Tag / 收藏 / 预设

- **我的 Tag**：面板“我的 Tag”页签，填英文 tag + 中文名 + 槽位，点“添加”。
  存到 `user/anima_prompt_studio/my_tags.json`，会进入统一目录的 `my` 分类，
  重启不丢。也可以“把当前手选存为我的 Tag”。
- **收藏**：卡片右上角星标，存 `studio_favorites.json`；侧栏“我的收藏”
  只显示收藏项。
- **最近使用**：面板自动记录最近点过的 60 个条目（localStorage）。
- **预设 / 历史**：把当前手选存成命名预设、导出/导入 JSON；存在浏览器
  localStorage，不跟工作流走。换机器请用导出/导入。

---

## 8. AI 预留接口（按你的要求暂不实现）

`ai_bridge.py` 定义：

- `AIProvider` 抽象类：`enhance(request) -> response`
- `NullProvider`：默认，永远返回“未启用”
- `StubOpenAICompatibleProvider`：给未来 OpenAI 兼容接口留的壳，不会发请求
- provider 注册表 + `contract()` 请求/响应契约

配置文件：

```text
<ComfyUI>/user/anima_prompt_studio/ai_providers.json
```

默认：

```json
{
  "enabled": false,
  "default": "null",
  "providers": []
}
```

行为：

- `GET /anima-prompt-studio/ai/status` 返回 `enabled: false`、provider 状态、
  契约摘要；
- `POST /anima-prompt-studio/ai/enhance` 在未启用时返回 **501**，**不会发起
  任何网络请求**；
- 前端“AI（预留）”页签只展示 provider 状态和契约，按钮故意禁用。

未来要做时：实现一个 provider、把它注册进 `ai_bridge.py`、把
`ai_providers.json` 的 `enabled` 改成 `true`，前端按钮就会自动放开。请求里
会带 `positive`、`negative`、`mode`、`level`、`locale`、`catalog_hint`，
响应按契约返回 `text` / `negative` / `notes` 等字段。

---

## 9. HTTP API

所有新路由前缀：`/anima-prompt-studio`。V6 路由也挂在同一前缀下（`/health`、
`/pools`、`/scenes`、`/characters`、`/thumb/...`、`/roll`、`/presets` 等）。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/catalog/meta` | 目录总览、分组、分类计数 |
| GET | `/catalog/items?cat=&q=&page=&limit=&level_max=&src=` | 分页搜索 |
| POST | `/catalog/by-ids` | 按 id 批量取回（托盘恢复） |
| POST | `/compose` | 三模式出词，返回 text/negative/report/counts |
| GET | `/studio/favorites` | 收藏 id + 条目 |
| POST | `/studio/favorites/toggle` | 收藏/取消 |
| GET | `/studio/my-tags` | 我的 Tag |
| POST | `/studio/my-tags/save` | 保存我的 Tag |
| GET | `/loras` | 本地 LoRA 列表 |
| POST | `/loras/meta` | 保存 LoRA 元数据/触发词 |
| GET | `/loras/stacks` | 命名堆栈 |
| POST | `/loras/stacks/save` | 保存堆栈 |
| POST | `/loras/stacks/delete` | 删除堆栈 |
| GET | `/ai/status` | AI 状态 + 契约 |
| GET | `/ai/contract` | 只取契约 |
| POST | `/ai/enhance` | 未启用返回 501 |
| GET | `/studio/health` | 插件自检：目录总数/分类数/AI/LoRA 数 |

V6 路由示例：`/health` 返回 V6 引擎统计（15 段 / 57 字段 / 1134 选项 /
524 场景 / 135 服装库）；`/thumb/hatsune_miku` 返回角色缩略图 webp。

---

## 10. 开发与测试

### 10.1 后端冒烟

```powershell
E:\Game\ComfyUI-Installs\Anima模型\ComfyUI\.venv\Scripts\python.exe `
  D:\Apps\99_Data\workbubby_Data\ComfyUI生图查看器\Comfyui-Anima-Prompt-Studio\tests\smoke_backend.py
```

覆盖：包加载、11 个节点、62,585 条目录、manual/hybrid/random 三种 compose、
手选报告不含 F1/F2、负面词、AI 未启用抛 `AIUnavailable`。

### 10.2 前端离线 harness

`tests/ui_harness/` 是一个不依赖 ComfyUI 的浏览器测试页：

```powershell
cd <插件>/tests/ui_harness
python -m http.server 8200 --bind 127.0.0.1
# 浏览器打开 http://127.0.0.1:8200/
```

它 mock 了 `scripts/app.js`、`scripts/api.js` 和目录/LoRA/AI 接口，实际渲染
主工坊面板，自动点卡片、预览、LoRA 加两条、下移排序、写回节点、切 AI/我的
Tag。页面底部 `#testlog` 会打印 `cards=12`、`preview=...`、`loraOrder...`、
`DONE` 等结果。2026-11-16 的 headless Edge 实测通过。

### 10.3 真机 ComfyUI

测试实例（独立端口 8199，不影响你正在用的 ComfyUI）：

```powershell
cd E:\Game\ComfyUI-Installs\Anima模型\ComfyUI
.\.venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8199 --cpu --disable-auto-launch
```

已实测：

- 插件 import `0.5s`，无报错；11 个节点注册成功；
- `/anima-prompt-studio/studio/health` 200，返回
  `catalog_total: 62585`、`catalog_cats: 31`、`loras: 21`；
- `/catalog/meta`、`/catalog/items?cat=artist&limit=3`、`/loras`、`/ai/status`、
  `/health`、`/studio/favorites`、`POST /compose` 全部 200；
- `/extensions/Comfyui-Anima-Prompt-Studio/studio.js` 200，52,441 bytes；
- `/anima-prompt-studio/thumb/hatsune_miku` 200，`image/webp`，10,138 bytes。
- 真实 ComfyUI 页面：节点库搜索 `AnimaPromptStudio` 能列出 11 个节点；插入主
  节点后点“🎨 打开提示词工坊”，面板正常渲染；点第一张卡片（1girl, solo）→
  “预览出词”返回 `1girl, solo` + 负面词；LoRA 页签列出本机 21 个 LoRA。
- `AnimaLoraStack` 的真实文件加载链已单独验证：`load_torch_file(path,
  safe_load=False)` + `load_lora_for_models` 两段 API 与 ComfyUI 0.45.3 的签名
  一致，并用一条真实 142MB LoRA 确认按数组顺序进入加载函数。
- 829px 窄视口下曾出现 LoRA 左列表被右侧托盘遮挡；已加 `@media` 响应式
  （侧栏/托盘收窄、LoRA 左右列改为上下堆叠），离线 harness 在 829×870 复测
  通过。

> 测试副本在 `custom_nodes/Comfyui-Anima-Prompt-Studio`；如果改项目目录里的
> 源码，要重新复制到 `custom_nodes` 才会被测试实例看到。

---

## 11. 已知边界（说清楚，不藏）

1. **没有做 Civitai 在线发现/下载**：LoRA 面板只管理本地 `models/loras`；
   堆栈、元数据、排序都可用。需要在线库时另加下载节点。
2. **Tools 的 5 个专用选择器合并成 1 个通用选择器**：`AnimaPromptStudioSelector`
   用 `category` 在画师/角色/服装/姿势/背景/构图/千藤/渡鸦等 12 类之间切换，
   功能等价，节点数量更少。
3. **V6 面板在工坊节点上只保留 1 个入口按钮**：V6 面板只加“打开随机面板”；
   “换种子/每次重抽/清空权重”三个按钮只在纯随机节点上出现。工坊入口由
   `js/nodes.js` 另加，所以一个节点总共是 2 个按钮，不再叠 6 个。
4. **角色目录按 id 去重**：V6 角色 2,432 条全部保留；此前按 `(cat, en)` 去重
   会合并同 trigger 的不同角色。
5. **手选报告不检查标签数量/质量词**：这是刻意设计；完整随机/混合仍走 V6
   的 17 项体检。
6. **真实 ComfyUI 页面已做基础点击实测**：插入节点、打开工坊、点卡片、预览出
   词都正常；LoRA 加/排序/写回在离线 harness 通过。修完窄视口 CSS 后没有在
   真实页面重跑一遍完整 LoRA 点击（浏览器测试后端在 reload 时卡住），但
   harness 在 829×870 下已复测。
7. **成人向内容**：词库含露骨标签，所有角色视为 18 岁以上虚构人物；请遵守
   所在地法律和平台政策。

---

## 12. 目录结构

```text
Comfyui-Anima-Prompt-Studio/
├── __init__.py                 # 11 个节点映射 + WEB_DIRECTORY + 路由注册
├── nodes_studio.py             # 主节点 / CLIP 编码 / 多框 / 选择器
├── nodes_lora.py               # 有序多 LoRA 加载器
├── nodes_danbooru.py           # Tools 的随机 Danbooru 节点（改名）
├── nodes_v6.py                 # V6 节点（改名）
├── routes_v6.py                # V6 HTTP 路由（前缀改为新插件）
├── routes_studio.py            # 目录 / compose / 收藏 / 我的Tag / LoRA / AI
├── catalog.py                  # 统一目录（62,585 条 / 31 类）
├── manual.py                   # manual / hybrid / random 出词
├── negative.py                 # 负面词基线 / 档位 / 冲突对
├── ai_bridge.py                # AIProvider 抽象 + 契约 + 默认关闭
├── anima_v4_*.py               # V6 引擎（原样内嵌）
├── js/
│   ├── v6_panel.js             # V6 面板（改前缀/节点类型）
│   ├── aps_common.js           # 公共样式 / Modal / 目录选择器
│   ├── lora_panel.js           # 可拖拽排序 LoraEditor
│   ├── studio.js               # 主工坊面板
│   └── nodes.js                # 节点按钮 / 隐藏内部控件
├── data/tools/                 # Tools 转换后的 JSON
├── presets/                    # V6 presets + 2432 张缩略图
├── tests/
│   ├── smoke_backend.py
│   └── ui_harness/
├── docs/
│   ├── 功能对照表.md
│   ├── 安装与升级.md
│   └── API.md
├── LICENSE                     # GPL-3.0 + 本插件衍生说明
└── THIRD_PARTY_NOTICES.md      # V6 / Tools 来源与许可
```

---

## 13. 来源与许可

- V6：https://github.com/lingdongbudong/Comfyui-Anima-Wardrobe-V6
  （作者：灵冻不冻，GPL-3.0）
- Anima-Tools：https://github.com/nregret/Comfyui-Anima-Tools
  （作者：nregret，MIT）
- PromptForge / 提示词生成器 v3.0：只作为产品思路参考，**未复制代码或数据**。

本插件按 GPL-3.0 发布；完整来源、改动范围、MIT 文本和免责声明见
`THIRD_PARTY_NOTICES.md`。角色名、作品名、画师名等知识产权归各自权利人。
