# -*- coding: utf-8 -*-
"""里程碑 G：ERP 领域 handler 由 ``xcagi-erp-domain-bridge`` Mod backend 分派。"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, is_erp_domain_via_mod_enabled

logger = logging.getLogger(__name__)


def _truthy_env(name: str) -> bool:
    import os

    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def is_erp_domain_handlers_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_ERP_DOMAIN_HANDLERS"):
        return False
    if _truthy_env("XCAGI_ERP_DOMAIN_HANDLERS"):
        return True
    if not is_erp_domain_via_mod_enabled():
        return False
    return _mod_domain_handler_domains() != []


def _mod_domain_handler_domains() -> list[str]:
    try:
        from pathlib import Path

        from app.mod_sdk.erp_domain_compat import _resolve_mod_dir

        mod_dir = _resolve_mod_dir()
        if not mod_dir:
            return []
        manifest = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
        cfg = manifest.get("config") or {}
        raw = cfg.get("mod_domain_handlers") or cfg.get("erp_domain_handlers") or []
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
    except Exception:
        logger.debug("read mod_domain_handlers failed", exc_info=True)
    return []


@lru_cache(maxsize=4)
def _load_domain_handlers_module(mod_path: str, mod_id: str):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    return import_mod_backend_py(mod_path, mod_id, "domain_handlers")


def _resolve_mod_path() -> tuple[str, str] | tuple[None, None]:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(ERP_DOMAIN_BRIDGE_MOD_ID)
        if meta and meta.mod_path:
            return ERP_DOMAIN_BRIDGE_MOD_ID, str(meta.mod_path)
    except Exception:
        logger.debug("erp domain mod path via manager failed", exc_info=True)

    from app.mod_sdk.erp_domain_compat import _resolve_mod_dir

    mod_dir = _resolve_mod_dir()
    if mod_dir:
        return ERP_DOMAIN_BRIDGE_MOD_ID, str(mod_dir)
    return None, None


def try_invoke_erp_domain_handler(
    domain: str,
    action: str,
    **kwargs: Any,
) -> Any | None:
    """若 Mod 已注册该领域动作则返回结果，否则 None（走宿主路由）。"""
    if not is_erp_domain_handlers_enabled():
        return None

    dom = str(domain or "").strip()
    act = str(action or "").strip()
    if not dom or not act:
        return None

    enabled_domains = _mod_domain_handler_domains()
    if enabled_domains and dom not in enabled_domains:
        return None

    mod_id, mod_path = _resolve_mod_path()
    if not mod_path:
        return None

    try:
        mod = _load_domain_handlers_module(mod_path, mod_id or ERP_DOMAIN_BRIDGE_MOD_ID)
        fn = getattr(mod, "run_domain_handler", None)
        if not callable(fn):
            return None
        out = fn(dom, act, **kwargs)
        if out is None:
            return None
        return out
    except Exception:
        logger.exception("erp domain handler failed domain=%s action=%s", dom, act)
        return {
            "success": False,
            "error": "erp_domain_handler_failed",
            "domain": dom,
            "action": act,
            "source": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
            "execution_path": "mod_domain_handler",
        }


def invoke_erp_domain_handler(domain: str, action: str, **kwargs: Any) -> Any:
    """Mod 门面路由用：优先 Mod handler，失败则抛给调用方 fallback。"""
    out = try_invoke_erp_domain_handler(domain, action, **kwargs)
    if out is not None:
        return out
    raise RuntimeError(f"erp domain handler missing: {domain}.{action}")


def list_erp_domain_handlers_summary() -> dict[str, Any]:
    domains = _mod_domain_handler_domains()
    mod_id, mod_path = _resolve_mod_path()
    actions: list[str] = []
    if mod_path:
        try:
            mod = _load_domain_handlers_module(mod_path, mod_id or ERP_DOMAIN_BRIDGE_MOD_ID)
            reg = getattr(mod, "list_registered_actions", None)
            if callable(reg):
                actions = list(reg())
        except Exception:
            logger.debug("list_registered_actions failed", exc_info=True)
    return {
        "enabled": is_erp_domain_handlers_enabled(),
        "mod_id": ERP_DOMAIN_BRIDGE_MOD_ID,
        "domains": domains,
        "action_count": len(actions),
        "actions": actions,
    }


__all__ = [
    "invoke_erp_domain_handler",
    "is_erp_domain_handlers_enabled",
    "list_erp_domain_handlers_summary",
    "try_invoke_erp_domain_handler",
]
