# -*- coding: utf-8 -*-
"""里程碑 K：ERP 业务 Vue 页经 ``xcagi-erp-domain-bridge`` Mod 路由提供。"""

from __future__ import annotations

from typing import Any

from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, is_erp_domain_via_mod_enabled

MOD_PAGE_PREFIX = f"/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}"

HOST_PAGES = [
    "/products",
    "/customers",
    "/orders",
    "/orders/create",
    "/shipment-records",
    "/wechat-contacts",
    "/materials",
    "/materials-list",
    "/traditional-mode",
    "/business-docking",
    "/data-sources",
    "/print",
    "/printer-list",
    "/template-preview",
    "/label-editor",
    "/purchase",
    "/inventory",
    "/batch-analyze",
]


def list_erp_pages_registry() -> dict[str, Any]:
    via = is_erp_domain_via_mod_enabled()
    return {
        "ok": True,
        "mod_id": ERP_DOMAIN_BRIDGE_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "page_count": len(HOST_PAGES),
        "pages_via_mod": via,
        "execution_path": "mod_pages" if via else "host.routes",
        "component_source": "mod.frontend.views (O+ physical)",
        "views_physical": True,
        "phase": "O+",
    }


__all__ = ["HOST_PAGES", "MOD_PAGE_PREFIX", "list_erp_pages_registry"]
