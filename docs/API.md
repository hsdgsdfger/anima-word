# HTTP API

前缀：`/anima-prompt-studio`。所有接口返回 JSON；错误返回
`{"ok": false, "error": "..."}`，必要时带 HTTP 状态码。

## 1. 目录

### `GET /catalog/meta`

返回总条数、分组、分类计数。

```json
{
  "total": 62585,
  "counts": {"quality": 8, "artist": 42197, "v6char": 2432, ...},
  "groups": [
    {"id": "base", "title": "基础词库",
     "cats": [{"key": "quality", "label": "✨ 质量与风格", "count": 8}, ...]},
    ...
  ]
}
```

### `GET /catalog/items`

查询参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `cat` | string | 分类 key，如 `artist`、`v6:hair`、`v6char`；空=全部 |
| `q` | string | 搜索英文/中文/id |
| `page` | int | 从 1 开始，默认 1 |
| `limit` | int | 默认 60，服务端有上限 |
| `level_max` | int/string | 最大档位；`none`/空=不限 |
| `src` | string | `v6` / `tools` / `my` |

返回：

```json
{"total": 42197, "page": 1, "limit": 3,
 "items": [{"id": "artist:qp_flapper-...", "cat": "artist",
            "en": "@qp:flapper", "zh": "qp:flapper", "slot": "artist",
            "level": 0, "src": "tools", "thumb": "", "tags": [],
            "extra": {"post_count": 16465}}]}
```

### `GET /catalog/random`

从**整个分类**随机抽一条，不受首屏分页 `limit` 限制。参数与
`/catalog/items` 相同，但没有 `page` / `limit`：

| 参数 | 类型 | 说明 |
|---|---|---|
| `cat` | string | 分类 key；空=全部 |
| `q` | string | 搜索过滤 |
| `level_max` | int/string | 最大档位；`none`/空=不限 |
| `src` | string | `v6` / `tools` / `builtin` / `my` |

返回：

```json
{"ok": true,
 "item": {"id": "v6:place:garden", "cat": "v6:scene", "en": "garden",
          "zh": "花园", "slot": "scene", "level": 0, "src": "v6"}}
```

当前分类没有可抽项时返回 `{"ok": true, "item": null}`。

### `POST /catalog/by-ids`

```json
{"ids": ["v6:hair:long hair", "artist:..."]}
```

返回 `{"ok": true, "items": [...]}`，用于面板恢复手选托盘。

## 2. 出词

### `POST /compose`

```json
{
  "studio_json": "{\"mode\":\"manual\",\"items\":[...]}",
  "widgets": {"nsfw_level": "sfw", "seed": 42, "tag_cap": "自动"}
}
```

`studio_json` 可以是 JSON 字符串，也可以是对象；`widgets` 缺省时用 V6 默认值。

返回：

```json
{
  "ok": true,
  "text": "masterpiece, best quality, (long hair:1.2), from above",
  "negative": "lowres, bad anatomy, ..., from below",
  "level": "sfw",
  "level_num": 0,
  "level_label": "0 · 全年龄",
  "cn_summary": "长发",
  "report": "模式 : 手选 ...",
  "counts": {"manual": 2, "total": 4},
  "fixes": []
}
```

## 3. 收藏 / 我的 Tag

### `GET /studio/favorites`

```json
{"ok": true, "ids": ["v6char:hatsune_miku"], "items": [...]}
```

### `POST /studio/favorites/toggle`

```json
{"id": "v6char:hatsune_miku"}
```

返回 `{"ok": true, "on": true, "ids": [...]}`。

### `GET /studio/my-tags`

```json
{"ok": true, "entries": [{"id": "my:...", "cat": "我的分类",
  "en": "my tag", "zh": "我的", "slot": "other", "level": 0, "note": ""}]}
```

### `POST /studio/my-tags/save`

```json
{"entries": [{"en": "my tag", "zh": "我的", "slot": "general"}]}
```

写入 `user/anima_prompt_studio/my_tags.json`，清目录缓存。

## 4. LoRA

### `GET /loras`

```json
{"ok": true, "count": 21,
 "items": [{"name": "anima-turbo-lora-v0.2.safetensors",
            "size": 148902616, "trigger": "", "note": "", "favorite": false}]}
```

### `POST /loras/meta`

```json
{"name": "style-a.safetensors",
 "patch": {"trigger": "style a", "note": "画风", "favorite": true}}
```

### `GET /loras/stacks`

```json
{"ok": true, "stacks": {"我的画风堆栈": {"entries": [...]}}}
```

### `POST /loras/stacks/save`

```json
{"name": "我的画风堆栈",
 "entries": [{"name": "style-a.safetensors", "strength_model": 0.8,
              "strength_clip": 0.8, "on": true, "trigger": "style a"}]}
```

### `POST /loras/stacks/delete`

```json
{"name": "我的画风堆栈"}
```

## 5. AI（预留）

### `GET /ai/status`

默认：

```json
{
  "enabled": false,
  "default": "null",
  "providers": [{"id": "null", "label": "未启用（占位）",
    "available": false, "reason": "AI 功能尚未启用；接口已预留...",
    "capabilities": []}],
  "message": "AI 功能暂缓；接口与 provider 注册表已就绪。",
  "contract": {"version": 1, "request": {...}, "response": {...}}
}
```

### `GET /ai/contract`

只返回 `contract`。

### `POST /ai/enhance`

未启用时：

```http
HTTP/1.1 501 Not Implemented
```

```json
{"ok": false, "code": "ai_not_enabled",
 "error": "AI 功能暂缓；接口与 provider 注册表已就绪。",
 "contract": {...}}
```

**不会发起任何网络请求。**

## 6. 自检

### `GET /studio/health`

```json
{"ok": true, "plugin": "anima-word",
 "catalog_total": 62585, "catalog_cats": 31, "ai": false, "loras": 21}
```

## 7. V6 路由

以下路由由 `routes_v6.py` 注册，前缀同为 `/anima-prompt-studio`：

- `GET /health`：V6 引擎统计（15 段 / 57 字段 / 1134 选项 / 524 场景 / 135 服装库）
- `GET /pools`、`POST /roll-options`、`POST /roll`
- `GET /scenes`、`GET /characters`、`GET /characters/detail`
- `GET /thumb/<tag>`：角色缩略图 webp
- `GET /presets`、`GET /favorites`、`POST /favorites`
- `GET /outfit-library` 及 override 系列
- `POST /characters/save|delete|reset|thumb|thumb-clear`

完整行为与 V6 一致，只是前缀换了。旧 V6 插件仍用自己的
`/anima-wardrobe-v6` 前缀，两者不冲突。
