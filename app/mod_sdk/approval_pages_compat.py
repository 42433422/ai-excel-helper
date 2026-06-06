# -*- coding: utf-8 -*-
"""里程碑 K：审批业务 Vue 页经 ``xcagi-approval-bridge`` Mod 路由提供。"""

from __future__ import annotations

from typing import Any

from app.mod_sdk.approval_compat import APPROVAL_BRIDGE_MOD_ID, is_approval_via_mod_enabled

MOD_PAGE_PREFIX = f"/mod/{APPROVAL_BRIDGE_MOD_ID}"

HOST_PAGES = [
    "/approval-hub",
    "/approval-hub/workspace",
    "/approval-hub/flow-management",
    "/approval-hub/rules",
]


def list_approval_pages_registry() -> dict[str, Any]:
    via = is_approval_via_mod_enabled()
    return {
        "ok": True,
        "mod_id": APPROVAL_BRIDGE_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "page_count": len(HOST_PAGES),
        "pages_via_mod": via,
        "execution_path": "mod_pages" if via else "host.routes",
        "component_source": "mod.frontend.views (O+ physical)",
        "views_physical": True,
        "phase": "O+",
    }


__all__ = ["HOST_PAGES", "MOD_PAGE_PREFIX", "list_approval_pages_registry"]
