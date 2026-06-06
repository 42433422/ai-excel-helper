# -*- coding: utf-8 -*-
"""里程碑 K：模型付费业务 Vue 页经 ``xcagi-model-payment-bridge`` Mod 路由提供。"""

from __future__ import annotations

from typing import Any

from app.mod_sdk.model_payment_compat import (
    MODEL_PAYMENT_BRIDGE_MOD_ID,
    is_model_payment_via_mod_enabled,
)

MOD_PAGE_PREFIX = f"/mod/{MODEL_PAYMENT_BRIDGE_MOD_ID}"

HOST_PAGES = ["/model-payment", "/kitten-finance"]


def list_model_payment_pages_registry() -> dict[str, Any]:
    via = is_model_payment_via_mod_enabled()
    return {
        "ok": True,
        "mod_id": MODEL_PAYMENT_BRIDGE_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "page_count": len(HOST_PAGES),
        "pages_via_mod": via,
        "execution_path": "mod_pages" if via else "host.routes",
        "component_source": "mod.frontend.views (O+ physical)",
        "views_physical": True,
        "phase": "O+",
    }


__all__ = ["HOST_PAGES", "MOD_PAGE_PREFIX", "list_model_payment_pages_registry"]
