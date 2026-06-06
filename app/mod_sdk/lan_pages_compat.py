# -*- coding: utf-8 -*-
"""里程碑 K：LAN 授权页经 Mod 路由提供（与宿主 /lan-gate 并存）。"""

from __future__ import annotations

from typing import Any

from app.mod_sdk.lan_compat import LAN_BRIDGE_MOD_ID, is_lan_via_mod_enabled

MOD_PAGE_PREFIX = f"/mod/{LAN_BRIDGE_MOD_ID}"

HOST_PAGES = ["/lan-gate"]


def list_lan_pages_registry() -> dict[str, Any]:
    via = is_lan_via_mod_enabled()
    return {
        "ok": True,
        "mod_id": LAN_BRIDGE_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "page_count": len(HOST_PAGES),
        "pages_via_mod": via,
        "host_route_preserved": True,
        "execution_path": "mod_pages" if via else "host.routes",
        "phase": "K",
    }


__all__ = ["HOST_PAGES", "MOD_PAGE_PREFIX", "list_lan_pages_registry"]
