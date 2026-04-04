"""
Mod 间直接通信（点对点调用）

与 Hook 的区别：
- Hook：系统或核心按事件名广播，多个订阅者，无返回值，不关心来源 Mod。
- Comms：调用方指定「目标 Mod + 通道名」，同步得到返回值；适合 Mod A 主动请求 Mod B 的能力。

使用方式（在 Mod 的 mod_init 或任意后端代码中）::

    from app.infrastructure.mods.comms import get_mod_comms, get_caller_mod_id

    def my_handler(query: str) -> dict:
        caller = get_caller_mod_id()  # 可选：获知调用方 mod id
        return {"echo": query}

    def mod_init():
        get_mod_comms().register("my-mod", "search", my_handler)

    # 自另一 Mod：
    get_mod_comms().call("caller-mod", "my-mod", "search", "hello")

通道名建议使用「点分层」避免冲突，例如 inventory.snapshot、pricing.quote。
"""

from __future__ import annotations

import contextvars
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

Handler = Callable[..., Any]

_current_caller: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "mod_comms_caller", default=None
)


class ModCommsError(Exception):
    """Mod 通信基础异常"""


class ModCommsNotFoundError(ModCommsError):
    """未注册的目标通道"""


class ModCommsConflictError(ModCommsError):
    """通道已被占用且未允许 replace"""


def get_caller_mod_id() -> Optional[str]:
    """在被 comms.call 调用的 handler 内部可读取当前调用方 mod id（无调用上下文时为 None）。"""
    return _current_caller.get()


class ModCommsRegistry:
    """按 (mod_id, channel) 注册的同步调用表。"""

    def __init__(self) -> None:
        self._handlers: Dict[Tuple[str, str], Handler] = {}

    def register(
        self,
        mod_id: str,
        channel: str,
        handler: Handler,
        *,
        replace: bool = False,
    ) -> None:
        mid = (mod_id or "").strip()
        ch = (channel or "").strip()
        if not mid or not ch:
            raise ValueError("mod_id and channel must be non-empty")
        if not callable(handler):
            raise TypeError("handler must be callable")
        key = (mid, ch)
        if key in self._handlers and not replace:
            raise ModCommsConflictError(f"Comms channel already registered: {mid}::{ch}")
        self._handlers[key] = handler
        logger.info("Mod comms registered: %s::%s -> %s", mid, ch, getattr(handler, "__name__", repr(handler)))

    def unregister(self, mod_id: str, channel: str) -> bool:
        mid = (mod_id or "").strip()
        ch = (channel or "").strip()
        return self._handlers.pop((mid, ch), None) is not None

    def unregister_all(self, mod_id: str) -> int:
        mid = (mod_id or "").strip()
        if not mid:
            return 0
        keys = [k for k in self._handlers if k[0] == mid]
        for k in keys:
            del self._handlers[k]
        if keys:
            logger.info("Mod comms cleared %d channel(s) for mod %s", len(keys), mid)
        return len(keys)

    def has_handler(self, target_mod_id: str, channel: str) -> bool:
        mid = (target_mod_id or "").strip()
        ch = (channel or "").strip()
        return (mid, ch) in self._handlers

    def call(
        self,
        source_mod_id: str,
        target_mod_id: str,
        channel: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """同步调用目标 Mod 在 channel 上注册的 handler，并将其返回值返回给调用方。"""
        src = (source_mod_id or "").strip() or "unknown"
        mid = (target_mod_id or "").strip()
        ch = (channel or "").strip()
        key = (mid, ch)
        fn = self._handlers.get(key)
        if fn is None:
            raise ModCommsNotFoundError(f"No comms handler: {mid}::{ch}")
        logger.debug("Mod comms call %s -> %s::%s", src, mid, ch)
        token = _current_caller.set(src)
        try:
            return fn(*args, **kwargs)
        finally:
            _current_caller.reset(token)

    def list_endpoints(self) -> List[Dict[str, str]]:
        """供调试或管理接口列举已注册端点（不含可调用对象）。"""
        out: List[Dict[str, str]] = []
        for (mid, ch), fn in sorted(self._handlers.items(), key=lambda x: (x[0][0], x[0][1])):
            out.append(
                {
                    "mod_id": mid,
                    "channel": ch,
                    "handler": getattr(fn, "__qualname__", getattr(fn, "__name__", type(fn).__name__)),
                }
            )
        return out


_registry: Optional[ModCommsRegistry] = None


def get_mod_comms() -> ModCommsRegistry:
    global _registry
    if _registry is None:
        _registry = ModCommsRegistry()
    return _registry
