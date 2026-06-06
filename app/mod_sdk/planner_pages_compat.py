# -*- coding: utf-8 -*-
"""里程碑 K：Planner 智能生态/智脑页经 ``xcagi-planner-bridge`` Mod 路由。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PLANNER_BRIDGE_MOD_ID = "xcagi-planner-bridge"
MOD_PAGE_PREFIX = f"/mod/{PLANNER_BRIDGE_MOD_ID}"

HOST_PAGES = ["/", "/ai-ecosystem", "/brain", "/chat-debug"]


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(PLANNER_BRIDGE_MOD_ID)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / PLANNER_BRIDGE_MOD_ID
    return trial if (trial / "manifest.json").is_file() else None


def is_planner_pages_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_PLANNER_PAGES_MOD"):
        return False
    if _truthy_env("XCAGI_PLANNER_PAGES_VIA_MOD"):
        return True
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return False
    try:
        cfg = (
            json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8")).get("config") or {}
        )
        return isinstance(cfg, dict) and cfg.get("planner_pages_via_mod") is True
    except Exception:
        return False


def list_planner_pages_registry() -> dict[str, Any]:
    via = is_planner_pages_via_mod_enabled()
    return {
        "ok": True,
        "mod_id": PLANNER_BRIDGE_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "chat_host_path": "/",
        "chat_mod_path": f"{MOD_PAGE_PREFIX}/chat",
        "page_count": len(HOST_PAGES),
        "pages_via_mod": via,
        "chat_via_mod": via,
        "component_source": "mod.frontend.views (P physical)",
        "views_physical": True,
        "phase": "P",
    }


__all__ = [
    "HOST_PAGES",
    "MOD_PAGE_PREFIX",
    "PLANNER_BRIDGE_MOD_ID",
    "is_planner_pages_via_mod_enabled",
    "list_planner_pages_registry",
]
