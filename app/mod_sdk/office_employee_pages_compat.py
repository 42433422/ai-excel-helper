# -*- coding: utf-8 -*-
"""里程碑 R：办公 employee_pack 业务页经 Mod 路由提供。"""

from __future__ import annotations

from typing import Any

OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID = "xcagi-office-employee-pack-bridge"
MOD_PAGE_PREFIX = f"/mod/{OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID}"

HOST_PAGES = ["/tools", "/other-tools"]


def list_office_employee_pages_registry() -> dict[str, Any]:
    return {
        "ok": True,
        "mod_id": OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "page_count": len(HOST_PAGES),
        "pages_via_mod": True,
        "component_source": "mod.frontend.views (R physical)",
        "views_physical": True,
        "phase": "R",
    }


__all__ = [
    "HOST_PAGES",
    "MOD_PAGE_PREFIX",
    "OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID",
    "list_office_employee_pages_registry",
]
