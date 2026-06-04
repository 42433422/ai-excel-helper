# -*- coding: utf-8 -*-
"""里程碑 K（客服）：外部/内部客服页经 ``xcagi-customer-service-bridge`` Mod 路由。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CUSTOMER_SERVICE_BRIDGE_MOD_ID = "xcagi-customer-service-bridge"
MOD_PAGE_PREFIX = f"/mod/{CUSTOMER_SERVICE_BRIDGE_MOD_ID}"

HOST_PAGES = ["/enterprise-customer-service", "/internal-customer-service"]


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(CUSTOMER_SERVICE_BRIDGE_MOD_ID)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / CUSTOMER_SERVICE_BRIDGE_MOD_ID
    return trial if (trial / "manifest.json").is_file() else None


def is_customer_service_pages_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_CUSTOMER_SERVICE_PAGES_MOD"):
        return False
    if _truthy_env("XCAGI_CUSTOMER_SERVICE_PAGES_VIA_MOD"):
        return True
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return False
    try:
        cfg = (
            json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8")).get("config") or {}
        )
        return isinstance(cfg, dict) and cfg.get("customer_service_pages_via_mod") is True
    except Exception:
        return False


def list_customer_service_pages_registry() -> dict[str, Any]:
    via = is_customer_service_pages_via_mod_enabled()
    physical = False
    try:
        from app.mod_sdk.mod_views_compat import is_mod_views_physical_enabled

        physical = is_mod_views_physical_enabled(CUSTOMER_SERVICE_BRIDGE_MOD_ID)
    except Exception:
        pass
    return {
        "ok": True,
        "mod_id": CUSTOMER_SERVICE_BRIDGE_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "page_count": len(HOST_PAGES),
        "pages_via_mod": via,
        "views_physical": physical,
        "component_source": "mod.frontend.views" if physical else "host.views lazy-import",
        "phase": "O" if physical else "K",
    }


__all__ = [
    "CUSTOMER_SERVICE_BRIDGE_MOD_ID",
    "HOST_PAGES",
    "MOD_PAGE_PREFIX",
    "is_customer_service_pages_via_mod_enabled",
    "list_customer_service_pages_registry",
]
