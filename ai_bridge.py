# -*- coding: utf-8 -*-
"""AI 预留接口（**默认完全关闭，不发任何网络请求**）。

为什么先留接口：
  · 「AI 参与的功能」需求还没定，现在接任何一家都会把 UI / 数据格式写死；
  · 但目录、手选、负面词、LoRA 堆栈都已经结构化，未来接 AI 只需要替换
    一个 provider，不用改节点和面板。

扩展方式（未来）：
  1. 写一个 `AIProvider` 子类，实现 `enhance()` / `suggest()`；
  2. 调 `register_provider(MyProvider())`；
  3. 在 `ComfyUI/user/anima_prompt_studio/ai_providers.json` 里把
     `"enabled": true`、`"default": "my-provider"`；
  4. 面板的 AI 页签会自动从「未启用」变成可用（`/ai/status` 驱动）。

当前所有 `/ai/enhance` 请求都会返回 501 + 契约说明，不会偷偷联网。
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod

_DEFAULT_CONTRACT = {
    "version": 1,
    "request": {
        "task": "enhance | suggest | translate | critique",
        "positive": "当前正向提示词",
        "negative": "当前负向提示词",
        "mode": "manual | hybrid | random",
        "level": "sfw | suggestive | explicit | hardcore | extreme",
        "locale": "zh-CN",
        "catalog_hint": "可选：当前选中的目录条目 id 数组",
        "max_tags": "可选：期望输出标签数上限",
    },
    "response": {
        "ok": "bool",
        "text": "增强后的正向提示词（task=enhance）",
        "negative": "可选：负向提示词",
        "tags": "可选：建议标签数组 [{en, zh, slot, w}]",
        "explanation": "可选：中文解释",
        "provider": "provider id",
    },
}


class AIUnavailable(RuntimeError):
    """AI 未启用 / provider 未配置。"""


class AIProvider(ABC):
    id = "abstract"
    label = "抽象 Provider"
    capabilities: tuple[str, ...] = ()

    @abstractmethod
    def available(self) -> tuple[bool, str]:
        """返回 (是否可用, 原因/提示)。"""

    @abstractmethod
    def enhance(self, payload: dict) -> dict:
        """执行一个 AI 任务。返回值必须符合 _DEFAULT_CONTRACT["response"]。"""


class NullProvider(AIProvider):
    id = "null"
    label = "未启用（占位）"
    capabilities = ()

    def available(self):
        return False, "AI 功能尚未启用；接口已预留，接入 provider 后自动开放。"

    def enhance(self, payload):
        raise AIUnavailable("AI 功能尚未启用（NullProvider）")


class StubOpenAICompatibleProvider(AIProvider):
    """OpenAI 兼容接口的占位实现 —— 只声明契约，不发起请求。

    真正启用时，在这里实现 HTTP 调用（base_url / api_key / model 从
    provider 配置读取），并保持 enhance() 的返回结构不变。
    """

    id = "openai-compatible"
    label = "OpenAI 兼容接口（未接线）"
    capabilities = ("enhance", "suggest", "translate", "critique")

    def __init__(self, config=None):
        self.config = config or {}

    def available(self):
        if not self.config.get("enabled"):
            return False, "provider 未启用（config.enabled=false）"
        if not self.config.get("base_url"):
            return False, "缺少 base_url"
        return False, "接口已预留，但本版本不实现网络调用（按需求暂缓 AI）"

    def enhance(self, payload):
        raise AIUnavailable(
            "OpenAI 兼容 provider 已登记，但本版本不发起网络请求。"
            "实现 enhance() 后再打开 config.enabled。")


_PROVIDERS: dict[str, AIProvider] = {"null": NullProvider()}
_DEFAULT = "null"


def user_dir():
    try:
        from . import catalog
    except ImportError:
        import catalog
    try:
        return catalog.user_data_path()
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")


def config_path():
    return os.path.join(user_dir(), "ai_providers.json")


def load_config():
    path = config_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("enabled", False)
    data.setdefault("default", "null")
    data.setdefault("providers", {})
    return data


def register_provider(provider):
    if not isinstance(provider, AIProvider):
        raise TypeError("provider 必须是 AIProvider 子类")
    _PROVIDERS[provider.id] = provider
    return provider


def _config_providers(config):
    """把配置文件里的 provider 条目实例化（目前只有 openai-compatible 占位）。"""
    out = {}
    for pid, cfg in (config.get("providers") or {}).items():
        if pid == "openai-compatible":
            out[pid] = StubOpenAICompatibleProvider(cfg)
    return out


def status():
    config = load_config()
    providers = dict(_PROVIDERS)
    providers.update(_config_providers(config))
    rows = []
    for pid, p in providers.items():
        ok, why = p.available()
        rows.append({"id": pid, "label": p.label, "available": bool(ok),
                     "reason": why, "capabilities": list(p.capabilities)})
    selected = str(config.get("default") or "null")
    enabled = bool(config.get("enabled")) and any(
        r["id"] == selected and r["available"] for r in rows)
    return {
        "enabled": enabled,
        "default": selected,
        "providers": rows,
        "message": ("AI 已启用" if enabled
                    else "AI 功能暂缓；接口与 provider 注册表已就绪。"),
        "contract": _DEFAULT_CONTRACT,
    }


def enhance(payload):
    """统一入口。未启用时抛 AIUnavailable，由路由转成 501。"""
    config = load_config()
    st = status()
    if not st["enabled"]:
        raise AIUnavailable(st["message"])
    pid = st["default"]
    providers = dict(_PROVIDERS)
    providers.update(_config_providers(config))
    p = providers.get(pid)
    if not p:
        raise AIUnavailable(f"找不到 provider：{pid}")
    ok, why = p.available()
    if not ok:
        raise AIUnavailable(why)
    result = p.enhance(dict(payload or {}))
    if not isinstance(result, dict):
        raise AIUnavailable("provider 返回格式不符合契约")
    result.setdefault("ok", True)
    result.setdefault("provider", pid)
    return result


def contract():
    return _DEFAULT_CONTRACT
