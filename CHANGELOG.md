# Changelog

## 1.0.7 — 2026-11-16

- 修复手动模式 `extra_body` 在 `repair()` 之后追加，导致重复、互斥、档位修复被绕过；
  现在与手选正文合并后统一修复，报告也按最终标签计算。
- 修复 `AnimaPromptStudioSelector` 的 `max_level` 只约束随机、不约束手选；
  手选条目同样按档位过滤，全部被过滤时不会再意外抽随机条目。
- 修复随机模式静默丢弃 `extra_text` / `manual_text` / `extra_body`；
  固定描述和手写补充现在会进入最终正文并经过统一修复。
- 修复 `hybrid + seed=-1` 的 `IS_CHANGED` 指纹稳定，导致持续命中旧缓存。
- 修复 Tools 服装目录默认 `level=0`，按 `R.tag_level()` 逐 tag 校准实际档位；
  SFW 服装目录不再混入规则引擎判为高档的条目。
- 修复负面词推导不解析 `(tag:weight)`，加权正向标签现在同样触发冲突词和回声过滤。
- 修复 `anima_v4_outfit_style.summary()` 引用未定义 `COLOR_TARGETS` 的 `NameError`。
- 修复目录允许只有中文、没有英文 tag 的幽灵条目；统一在 `_item()` 剔除空 `en`。
- 新增 `tests/test_bugfixes.py`，覆盖以上 8 项；现有 smoke / 元数据 / 权重 / 语法回归全部通过。

## 1.0.6 — 2026-11-16

- 提示词工坊顶部改为固定三页签：`权重库 / 提示词 / 预设`，默认进入 `权重库`。
- `提示词` 页分 `模板 / 通用`：模板为 V6 原版并隐藏右侧预览/手选托盘；
  通用显示目录、托盘和预览，且强制手选模式。
- 权重库与随机只控制模板；模板新增“固定描述（随机时保留）”。
- 权重统一到 `0–5`：0 不出现，5 必定出现，1–4 概率递增；完整 V6 面板、
  场景必现、互斥降级、手动权重上限同步到 5.0。
- 左侧“已保存的权重”改为单入口；支持保存/应用/删除多条权重库。
- 手选托盘只显示提示词文字和行尾删除符号；收藏星标增加 pointer 隔离。
- 提示词预览按人物、外貌、服装、姿势、风格、镜头、场景、光照分组。
- 主节点控件增加中文显示名，输出名改为中文；专有名词与键名保持不变。
- 修复 `/studio/my-tags` 返回 `items` 时“我的 Tag”空白；修复旧页签
  `v6full` 无入口导致的空引用；修复测试 harness 与新默认页不同步的问题。

## 1.0.5 — 2026-11-16

- 并入旧 `ComfyUI-AnimaPromptDecoupler` 的“V6 正文 → 真正提示词”逻辑，
  新模块 `prompt_decouple.py`（纯标准库，不注册节点、不提供 UI）。
- 元数据入口默认启用转换；主节点 `text` 输出仍是 V6 原文，不影响采样。
- PNG/API 元数据 `anima_v4_prompt` / `anima_v3_prompt` 的 `positive` 改为
  转换后的真正提示词，新增 `positive_raw` 保存 V6 原文；新增 `prompt_nl`、
  `prompt_negative`、`conversion` 字段。
- `OWN_TEXT_OUTPUT_SLOT` 补入 `AnimaPromptStudio`、`AnimaPromptStudioRandom`
  及 V6/V5/V4/V3 随机节点，修复主节点工作流元数据定位。
- 新增 `tests/test_prompt_metadata.py`，覆盖转换、原文保留和 Studio 节点种子。

## 1.0.4 — 2026-11-16

- 删除主工坊面板里的 `LoRA` 页签、LoRA 状态和 `lora_json` 输出。
- `AnimaPromptStudio` 输出从 6 个变为 5 个：
  `text / report / level / cn_summary / negative`。
- 保留独立的 `AnimaLoraStack` 多 LoRA 加载器节点及其可拖拽排序面板；
  它继续直接读取 `models/loras`，数组下标就是加载顺序。
- 用户数据目录 `user/anima_prompt_studio` 不变。

## 1.0.3 — 2026-11-16

- 对外插件名改为 `anima-word`：安装目录、GitHub 仓库、zip、面板标题、
  节点显示名同步更新。
- 为兼容已有工作流，节点类名 `AnimaPromptStudio*`、`AnimaLoraStack` 和
  路由前缀 `/anima-prompt-studio` 保持不变。
- 用户数据目录 `user/anima_prompt_studio` 不变，旧收藏、我的 Tag、
  LoRA 堆栈和 AI provider 配置继续可用。

## 1.0.2 — 2026-11-16

- 目录页新增「🎲 随机一条 / 随机场景」：场景相关分类自动显示为「随机场景」，
  从整个分类随机抽取，不受首屏 60 条限制；支持搜索、来源、SFW 档位过滤。
- 新增 `GET /anima-prompt-studio/catalog/random`，返回一条随机目录项。
- 抽到的条目直接进入手选托盘，可在手选 / 混合模式里继续调权重与顺序。

## 1.0.1 — 2026-11-16

复查修复版。只改本插件源码，不改变节点类名、路由前缀和用户数据结构。

### 修复

- **混合模式丢失手选权重**：`compose_hybrid()` 合并时改用 repair 后的标签，
  再按手选条目的原始权重重新套括号；`(long hair:1.6)` 不再退化成 `long hair`。
- **混合模式角色/外貌冲突**：`v6char` / `character` 现在同时覆盖
  `count / hair / face / body / makeup`；手选角色或手选外貌标签时关闭随机
  角色与 `appearance_follow`，避免再补一个角色或注入官方发色/瞳色。
- **混合模式 `extra_body` 重复**：节点补充词只合并一次，不再同时进入随机
  结果和最终结果。
- **选择器节点随机模式崩溃**：`AnimaPromptStudioSelector` 原来把 `cat`
  写成 `category=`，会抛 `TypeError`；已改为 `catalog.sample()`，并从整个
  分类抽样，不再只抽前 500 条。
- **目录来源筛选失效**：前端从 `source` 改成后端实际的 `src` 参数；
  “V6 词库 / Anima-Tools / 内置质量词 / 我的 Tag”现在真正过滤。
- **按槽位排序时托盘移动无效**：上下移动/拖拽会自动切到“手选顺序”，
  视觉顺序与底层 `items` 顺序一致。
- **LoRA 同名文件替换不刷新**：`IS_CHANGED` 现在把 JSON、文件大小和
  `mtime_ns` 一起纳入缓存指纹。
- **`/studio/my-tags/save` 非法 level 500**：改为安全解析并夹在 0-4。
- **关闭工坊面板丢最后一次修改**：`Modal.onClose` 立即写回 `studio_json`，
  不再只依赖 300ms debounce。

### 验证

- `tests/smoke_backend.py`：`ALL OK`（11 节点、62585 条目录、三种模式、
  混合权重、来源筛选、选择器随机）。
- 离线 UI harness：来源筛选 `srcTools=1 / @test`；槽位排序下移后
  `reorder=custom`；829×870 下 LoRA 左右两栏 `overlap=false`。
- 真实 ComfyUI 0.45.3：`/object_info/AnimaPromptStudio` 6 个输出、optional
  含 `mode/studio_json/manual_text`；`/catalog/meta` 62585/31；`/loras` 21；
  `/compose` 返回 `(long hair:1.6)`。
- 真实 142MB LoRA 仍可经 `load_torch_file(path, safe_load=False)` 加载，
  并按数组顺序进入 `load_lora_for_models`。

## 1.0.0 — 2026-11-15

首个独立插件包：V6 引擎内嵌、统一目录、三模式出词、可排序多 LoRA 加载器、
AI provider 预留接口（默认关闭）、V6 面板与工坊面板。
