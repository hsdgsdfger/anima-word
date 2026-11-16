# -*- coding: utf-8 -*-
"""新插件自己的 HTTP 路由：目录 / 手选预览 / LoRA 顺序 / 我的 Tag / AI 占位。

与 routes_v6.py 共用 `/anima-prompt-studio` 前缀，但路径刻意错开：
V6 已占用 pools / contract / scenes / characters / thumb / roll /
presets / favorites / outfit-library / health，本文件一律避开。
"""
from __future__ import annotations

import os
import time

try:
    from . import ai_bridge
    from . import catalog
    from . import manual
    from .nodes_lora import (
        delete_stack, list_loras, list_stacks, save_meta, save_stack,
    )
except ImportError:  # 独立测试环境
    import ai_bridge
    import catalog
    import manual
    from nodes_lora import (
        delete_stack, list_loras, list_stacks, save_meta, save_stack,
    )

PREFIX = "/anima-prompt-studio"


def _err(msg, status=400):
    from aiohttp import web
    return web.json_response({"ok": False, "error": str(msg)}, status=status)


def register():
    try:
        from aiohttp import web
        from server import PromptServer
    except Exception as exc:  # pragma: no cover
        print(f"[AnimaPromptStudio] 无法注册新路由: {exc}")
        return False

    routes = PromptServer.instance.routes

    def get(path):
        return routes.get(PREFIX + path)

    def post(path):
        return routes.post(PREFIX + path)

    async def _body(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        return data if isinstance(data, dict) else {}

    @get("/catalog/meta")
    async def _catalog_meta(request):
        return web.json_response(catalog.meta())

    @get("/catalog/items")
    async def _catalog_items(request):
        q = request.query
        try:
            page = int(q.get("page", 1))
            limit = int(q.get("limit", 60))
        except ValueError:
            page, limit = 1, 60
        level_max = q.get("level_max")
        if level_max in ("", "none", "不限", None):
            level_max = None
        try:
            res = catalog.items(
                cat=q.get("cat", ""), q=q.get("q", ""), page=page, limit=limit,
                level_max=level_max, src=q.get("src", ""))
        except Exception as exc:
            return _err(f"目录读取失败：{exc}", 500)
        return web.json_response(res)

    @post("/catalog/by-ids")
    async def _catalog_by_ids(request):
        body = await _body(request)
        ids = body.get("ids") or []
        if not isinstance(ids, list):
            return _err("ids 必须是数组")
        return web.json_response({"ok": True, "items": catalog.get_by_ids(ids[:500])})

    @get("/studio/favorites")
    async def _favorites(request):
        path = catalog.user_data_path("studio_favorites.json")
        try:
            import json
            with open(path, "r", encoding="utf-8") as fh:
                ids = json.load(fh)
        except Exception:
            ids = []
        if not isinstance(ids, list):
            ids = []
        return web.json_response({"ok": True, "ids": ids,
                                  "items": catalog.get_by_ids(ids[:500])})

    @post("/studio/favorites/toggle")
    async def _favorites_toggle(request):
        import json
        body = await _body(request)
        item_id = str(body.get("id") or "").strip()
        if not item_id:
            return _err("缺少 id")
        path = catalog.user_data_path("studio_favorites.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                ids = json.load(fh)
            if not isinstance(ids, list):
                ids = []
        except Exception:
            ids = []
        if item_id in ids:
            ids.remove(item_id)
            on = False
        else:
            ids.insert(0, item_id)
            on = True
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(ids[:3000], fh, ensure_ascii=False)
        os.replace(tmp, path)
        return web.json_response({"ok": True, "on": on, "ids": ids})

    @post("/compose")
    async def _compose(request):
        body = await _body(request)
        studio = body.get("studio_json") or body.get("studio") or {}
        widgets = body.get("widgets") if isinstance(body.get("widgets"), dict) else {}
        # 缺省值对齐 V6 节点
        defaults = {
            "nsfw_level": "sfw", "seed": -1, "tag_cap": "自动",
            "base_prob": 0.65, "disabled_sections": "", "lock_fields": "",
            "force_role": "", "weights_json": "", "extra_body": "",
            "appearance_follow": True, "selected_roles": "",
            "big_breasts": False, "role_works": "", "breast_size": "不指定",
            "outfit_style": "随机", "role_fav_only": False, "hair_follow": True,
            "hair_len_pick": "", "hair_tie_pick": "", "hair_curl_pick": "",
            "hair_acc_pick": "", "role_pick": True, "scene_pick": False,
            "dry_skin_filter": False, "dry_skin_groups": "", "dry_skin_tags": "",
            "duo_role_fill": True, "pick_pool_mode": "", "pick_pool_ids": "",
        }
        kwargs = dict(defaults)
        kwargs.update({k: v for k, v in widgets.items() if k in defaults})
        try:
            res = manual.compose(studio, kwargs)
        except Exception as exc:
            return _err(f"出词失败：{exc}", 500)
        return web.json_response({
            "ok": True,
            "text": res["text"],
            "negative": res.get("negative", ""),
            "level": res["level"],
            "level_num": res["level_num"],
            "level_label": res["level_label"],
            "cn_summary": res["cn_summary"],
            "report": res["report_text"],
            "counts": res["counts"],
            "fixes": res.get("fixes") or [],
        })

    @get("/studio/my-tags")
    async def _my_tags(request):
        import json
        path = catalog.user_data_path("my_tags.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {"entries": []}
        if not isinstance(data, dict):
            data = {"entries": []}
        data.setdefault("entries", [])
        return web.json_response({"ok": True, **data})

    @post("/studio/my-tags/save")
    async def _my_tags_save(request):
        import json
        body = await _body(request)
        entries = body.get("entries")
        if not isinstance(entries, list):
            return _err("entries 必须是数组")
        cleaned = []
        for e in entries[:5000]:
            if not isinstance(e, dict):
                continue
            en = str(e.get("en") or "").strip()
            if not en:
                continue
            try:
                level = int(e.get("level") or 0)
            except (TypeError, ValueError):
                level = 0
            cleaned.append({
                "id": str(e.get("id") or "").strip() or f"my:{en[:60]}",
                "cat": str(e.get("cat") or "我的分类")[:40],
                "en": en[:400],
                "zh": str(e.get("zh") or en)[:80],
                "slot": str(e.get("slot") or "other")[:20],
                "level": max(0, min(4, level)),
                "note": str(e.get("note") or "")[:400],
            })
        path = catalog.user_data_path("my_tags.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"entries": cleaned, "updated": int(time.time())},
                      fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        catalog.clear_cache()
        return web.json_response({"ok": True, "entries": cleaned,
                                  "count": len(cleaned)})

    @get("/loras")
    async def _loras(request):
        try:
            rows = list_loras()
        except Exception as exc:
            return _err(f"LoRA 列表读取失败：{exc}", 500)
        return web.json_response({"ok": True, "items": rows, "count": len(rows)})

    @post("/loras/meta")
    async def _loras_meta(request):
        body = await _body(request)
        name = str(body.get("name") or "").strip()
        patch = body.get("patch") if isinstance(body.get("patch"), dict) else {}
        if not name:
            return _err("缺少 name")
        try:
            rec = save_meta(name, patch)
        except Exception as exc:
            return _err(f"保存失败：{exc}", 500)
        return web.json_response({"ok": True, "meta": rec})

    @get("/loras/stacks")
    async def _stacks(request):
        return web.json_response({"ok": True, "stacks": list_stacks()})

    @post("/loras/stacks/save")
    async def _stack_save(request):
        body = await _body(request)
        try:
            rec = save_stack(body.get("name"), body.get("entries") or [])
        except Exception as exc:
            return _err(f"保存失败：{exc}")
        return web.json_response({"ok": True, "stack": rec})

    @post("/loras/stacks/delete")
    async def _stack_delete(request):
        body = await _body(request)
        try:
            delete_stack(body.get("name"))
        except Exception as exc:
            return _err(f"删除失败：{exc}")
        return web.json_response({"ok": True})

    @get("/ai/status")
    async def _ai_status(request):
        return web.json_response(ai_bridge.status())

    @get("/ai/contract")
    async def _ai_contract(request):
        return web.json_response(ai_bridge.contract())

    @post("/ai/enhance")
    async def _ai_enhance(request):
        body = await _body(request)
        try:
            return web.json_response({"ok": True, **ai_bridge.enhance(body)})
        except ai_bridge.AIUnavailable as exc:
            return web.json_response({
                "ok": False,
                "code": "ai_not_enabled",
                "error": str(exc),
                "contract": ai_bridge.contract(),
            }, status=501)

    @get("/studio/health")
    async def _health(request):
        meta = catalog.meta()
        return web.json_response({
            "ok": True,
            "plugin": "Comfyui-Anima-Prompt-Studio",
            "catalog_total": meta["total"],
            "catalog_cats": len(meta["counts"]),
            "ai": ai_bridge.status()["enabled"],
            "loras": len(list_loras()) if _has_folder_paths() else 0,
        })

    print(f"[AnimaPromptStudio] 新路由已注册: catalog / compose / studio / loras / ai")
    return True


def _has_folder_paths():
    try:
        import folder_paths  # noqa: F401
        return True
    except Exception:
        return False
