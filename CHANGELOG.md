# Changelog

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
