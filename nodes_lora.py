# -*- coding: utf-8 -*-
"""可自由排序的多 LoRA 加载器。

与 Anima-Tools 的 `AnimaMultiLoraLoader` 的区别：
  · `lora_list_json` 是**有序数组**，数组下标就是应用顺序；面板拖拽 /
    上移下移直接改数组，不再依赖"添加顺序"这种隐形状态。
  · 每项独立 `strength_model` / `strength_clip` / `on` / `trigger`。
  · 输出 `triggers`（触发词）和 `report`（实际应用顺序），方便排查。
  · 保存 / 读取命名堆栈（预设），顺序一并保存。

节点只依赖 ComfyUI 的 `folder_paths` 与 `comfy.sd`；测试环境没有它们时，
导入函数内部会给出清晰错误，不会在模块导入阶段炸掉。
"""
from __future__ import annotations

import json
import os
import time
import zlib

try:
    from . import anima_v4_rules as R  # 只为 CATEGORY 文案复用；不参与计算
except ImportError:  # 独立测试环境
    import anima_v4_rules as R


def _json(raw, default):
    try:
        v = json.loads(raw) if str(raw or "").strip() else default
        return v
    except Exception:
        return default


def _folder_paths():
    try:
        import folder_paths
        return folder_paths
    except Exception:
        return None


def _user_dir():
    try:
        try:
            from . import catalog
        except ImportError:
            import catalog
        return catalog.user_data_path()
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")


def _meta_path():
    return os.path.join(_user_dir(), "lora_meta.json")


def _load_meta():
    path = _meta_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_meta(data):
    path = _meta_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def list_loras():
    """本地 LoRA 列表（名称 / 大小 / 修改时间 / 用户元数据）。"""
    fp = _folder_paths()
    if fp is None:
        return []
    try:
        names = fp.get_filename_list("loras")
    except Exception:
        return []
    meta = _load_meta()
    out = []
    for name in names:
        full = ""
        try:
            full = fp.get_full_path("loras", name) or ""
        except Exception:
            full = ""
        try:
            st = os.stat(full) if full else None
            size = st.st_size if st else 0
            mtime = int(st.st_mtime) if st else 0
        except OSError:
            size, mtime = 0, 0
        rec = meta.get(name) or {}
        out.append({
            "name": name,
            "base": os.path.basename(name),
            "size": size,
            "mtime": mtime,
            "trigger": rec.get("trigger", ""),
            "note": rec.get("note", ""),
            "base_model": rec.get("base_model", ""),
            "favorite": bool(rec.get("favorite", False)),
            "preview": rec.get("preview", ""),
        })
    out.sort(key=lambda x: (not x["favorite"], x["name"].lower()))
    return out


def resolve_name(name):
    """把用户传的名字解析成 folder_paths 里的真实文件名。"""
    fp = _folder_paths()
    name = str(name or "").strip()
    if fp is None or not name:
        return ""
    try:
        names = fp.get_filename_list("loras")
    except Exception:
        return ""
    if name in names:
        return name
    low = name.lower()
    for n in names:
        if n.lower() == low:
            return n
    for n in names:
        if os.path.basename(n).lower() == os.path.basename(low):
            return n
    for n in names:
        if low in n.lower():
            return n
    return ""


def save_meta(name, patch):
    """保存单个 LoRA 的触发词 / 备注 / 基础模型 / 收藏。"""
    name = resolve_name(name) or str(name or "").strip()
    if not name:
        raise ValueError("LoRA 名不能为空")
    data = _load_meta()
    rec = data.get(name) if isinstance(data.get(name), dict) else {}
    for key in ("trigger", "note", "base_model", "preview"):
        if key in patch:
            rec[key] = str(patch.get(key) or "")[:400]
    if "favorite" in patch:
        rec["favorite"] = bool(patch.get("favorite"))
    data[name] = rec
    _save_meta(data)
    return rec


def stack_path():
    return os.path.join(_user_dir(), "lora_stacks.json")


def list_stacks():
    try:
        with open(stack_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_stack(name, entries):
    name = str(name or "").strip()[:40]
    if not name:
        raise ValueError("堆栈名不能为空")
    data = list_stacks()
    data[name] = {
        "entries": entries if isinstance(entries, list) else [],
        "updated": int(time.time()),
    }
    os.makedirs(os.path.dirname(stack_path()), exist_ok=True)
    tmp = stack_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, stack_path())
    return data[name]


def delete_stack(name):
    data = list_stacks()
    data.pop(str(name or "").strip(), None)
    tmp = stack_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, stack_path())
    return True


class AnimaLoraStack:
    """按数组顺序应用 LoRA。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "lora_list_json": ("STRING", {"default": "[]", "multiline": False,
                                              "tooltip": "有序数组；下标即应用顺序"}),
            },
            "optional": {
                "clip": ("CLIP",),
                "default_strength": ("FLOAT", {"default": 1.0, "min": -10.0,
                                               "max": 10.0, "step": 0.05}),
                "stop_on_error": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING")
    RETURN_NAMES = ("model", "clip", "triggers", "report")
    FUNCTION = "apply"
    CATEGORY = "AnimaPromptStudio"

    @classmethod
    def IS_CHANGED(cls, model=None, lora_list_json="[]", clip=None,
                   default_strength=1.0, stop_on_error=False):
        """把 JSON + 实际 LoRA 文件指纹一起纳入缓存判断。

        只哈希 JSON 的话，用户替换同名 LoRA 文件（不改变列表）时，ComfyUI
        会认为节点没变而复用上一次的加载结果；把 size / mtime_ns 加进来
        才能让“同名文件更新”真正触发重新加载。
        """
        rows = _json(lora_list_json, [])
        if isinstance(rows, dict):
            rows = rows.get("entries") or []
        if not isinstance(rows, list):
            rows = []
        bits = [str(default_strength), str(bool(stop_on_error))]
        fp = _folder_paths()
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_name = str(row.get("name") or "").strip()
            if not raw_name:
                continue
            name = resolve_name(raw_name) if fp is not None else ""
            bits.append(name or raw_name)
            if fp is None or not name:
                continue
            try:
                full = fp.get_full_path("loras", name) or ""
                if full:
                    st = os.stat(full)
                    bits.append(f"{st.st_size}:{st.st_mtime_ns}")
            except Exception:
                bits.append("missing")
        return zlib.crc32("|".join(bits).encode("utf-8"))

    def apply(self, model, lora_list_json="[]", clip=None,
              default_strength=1.0, stop_on_error=False):
        fp = _folder_paths()
        if fp is None:
            raise RuntimeError("当前环境没有 ComfyUI 的 folder_paths，无法加载 LoRA")

        rows = _json(lora_list_json, [])
        if isinstance(rows, dict):
            rows = rows.get("entries") or []
        if not isinstance(rows, list):
            rows = []

        try:
            import comfy.sd
            import comfy.utils
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"当前环境没有 comfy 模块：{exc}") from exc

        triggers, report = [], []
        idx = 0
        for row in rows:
            if not isinstance(row, dict) or row.get("on") is False:
                continue
            raw_name = str(row.get("name") or "").strip()
            if not raw_name:
                continue
            name = resolve_name(raw_name)
            if not name:
                msg = f"跳过：找不到 LoRA「{raw_name}」"
                report.append(msg)
                if stop_on_error:
                    raise FileNotFoundError(msg)
                continue
            try:
                sm = float(row.get("strength_model", row.get("strength", default_strength)))
            except (TypeError, ValueError):
                sm = float(default_strength)
            try:
                sc = float(row.get("strength_clip", row.get("strength", default_strength)))
            except (TypeError, ValueError):
                sc = float(default_strength)
            try:
                path = fp.get_full_path("loras", name)
                if not path:
                    raise FileNotFoundError(name)
                lora = comfy.utils.load_torch_file(path, safe_load=False)
                model, clip = comfy.sd.load_lora_for_models(
                    model, clip, lora, sm, sc)
                idx += 1
                trig = str(row.get("trigger") or "").strip()
                if trig:
                    triggers.extend([t.strip() for t in trig.split(",") if t.strip()])
                report.append(f"{idx:02d}. {name}  model {sm:g} / clip {sc:g}")
            except Exception as exc:
                msg = f"失败：{name} —— {exc}"
                report.append(msg)
                if stop_on_error:
                    raise
        text = ", ".join(dict.fromkeys(triggers))
        header = f"有序应用 {idx} 个 LoRA（数组顺序）"
        return (model, clip, text, "\n".join([header] + report))


NODE_CLASS_MAPPINGS = {
    "AnimaLoraStack": AnimaLoraStack,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaLoraStack": "Anima 多 LoRA 加载器（可排序）",
}
