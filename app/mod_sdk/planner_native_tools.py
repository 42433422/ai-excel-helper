# -*- coding: utf-8 -*-
"""里程碑 F：Planner 工具 handler 由 Mod backend 提供（优先于宿主 workflow）。"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

PLANNER_EXCEL_TOOLS_MOD_ID = "xcagi-planner-excel-tools"


def _truthy_env(name: str) -> bool:
    import os

    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def is_planner_native_tools_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_PLANNER_NATIVE_TOOLS"):
        return False
    if _truthy_env("XCAGI_PLANNER_NATIVE_TOOLS"):
        return True
    return _discover_native_tool_mods() != []


def _discover_native_tool_mods() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

        if is_mods_disabled():
            return rows
        mgr = get_mod_manager()
        for meta in mgr.list_loaded_mods():
            tools = _native_tools_from_metadata(meta)
            if tools:
                rows.append(
                    {
                        "mod_id": meta.id,
                        "mod_path": meta.mod_path,
                        "tool_names": tools,
                    }
                )
    except Exception:
        logger.debug("discover native planner mods via loaded failed", exc_info=True)

    if rows:
        return rows

    # 磁盘扫描（Mod 未热加载时）
    try:
        from app.infrastructure.mods.manifest import parse_manifest
        from app.shell.xcagi_mods_discover import mods_dir

        root = mods_dir()
        if not root:
            return rows
        from pathlib import Path

        for child in Path(root).iterdir():
            if not child.is_dir() or child.name.startswith("_"):
                continue
            meta = parse_manifest(str(child))
            if not meta:
                continue
            tools = _native_tools_from_metadata(meta)
            if tools:
                rows.append({"mod_id": meta.id, "mod_path": meta.mod_path, "tool_names": tools})
    except Exception:
        logger.debug("discover native planner mods via disk failed", exc_info=True)
    return rows


def _native_tools_from_metadata(meta: Any) -> list[str]:
    try:
        manifest_path = __import__("pathlib").Path(meta.mod_path) / "manifest.json"
        if not manifest_path.is_file():
            return []
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        cfg = data.get("config") or {}
        raw = cfg.get("native_planner_tools") or cfg.get("planner_native_tools") or []
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
    except Exception:
        pass
    return []


@lru_cache(maxsize=8)
def _load_handler_module(mod_path: str, mod_id: str):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    return import_mod_backend_py(mod_path, mod_id, "tool_handlers")


def try_execute_native_planner_tool(
    name: str,
    args: dict[str, Any] | str,
    workspace_root: str | None = None,
    *,
    db_write_token: str | None = None,
) -> tuple[str | None, str | None]:
    """若 Mod 已注册该工具则返回 (result_json, mod_id)，否则 (None, None)。"""
    if not is_planner_native_tools_enabled():
        return None, None

    tool = str(name or "").strip()
    if not tool:
        return None, None

    for row in _discover_native_tool_mods():
        if tool not in row.get("tool_names") or []:
            continue
        mod_id = str(row.get("mod_id") or "")
        mod_path = str(row.get("mod_path") or "")
        if not mod_path:
            continue
        try:
            mod = _load_handler_module(mod_path, mod_id)
            fn = getattr(mod, "run_native_tool", None)
            if not callable(fn):
                continue
            out = fn(
                tool,
                args,
                workspace_root=workspace_root,
                db_write_token=db_write_token,
            )
            if out is None:
                continue
            return str(out), mod_id
        except Exception:
            logger.exception("native planner tool failed mod=%s tool=%s", mod_id, tool)
            return (
                json.dumps(
                    {"success": False, "error": "native_tool_failed", "mod_id": mod_id},
                    ensure_ascii=False,
                ),
                mod_id,
            )
    return None, None


def list_native_planner_tools_summary() -> dict[str, Any]:
    mods = _discover_native_tool_mods()
    all_names: list[str] = []
    for m in mods:
        all_names.extend(m.get("tool_names") or [])
    return {
        "enabled": is_planner_native_tools_enabled(),
        "mod_count": len(mods),
        "mods": mods,
        "tool_names": sorted(set(all_names)),
    }


__all__ = [
    "PLANNER_EXCEL_TOOLS_MOD_ID",
    "is_planner_native_tools_enabled",
    "list_native_planner_tools_summary",
    "try_execute_native_planner_tool",
]
