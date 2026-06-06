# -*- coding: utf-8 -*-
"""里程碑 B：Planner 工具经 ``xcagi-planner-bridge`` 门面执行与注册。

安装 Planner Mod 且 ``planner_tools_execution`` 为真时，对话链与 ``/tools/execute`` 走本模块，
再委托宿主 ``execute_workflow_tool``（实现仍在宿主，边界在 Mod API）。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

PLANNER_FACADE_MOD_ID = "xcagi-planner-bridge"

logger = logging.getLogger(__name__)

ExecuteToolFn = Callable[..., str]


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_planner_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(PLANNER_FACADE_MOD_ID)
        if meta and meta.mod_path:
            p = Path(meta.mod_path)
            if (p / "manifest.json").is_file():
                return p
    except Exception:
        logger.debug("planner mod path via manager failed", exc_info=True)

    roots: list[Path] = []
    for key in ("XCAGI_MODS_ROOT", "XCAGI_MODS_DIR"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            roots.append(Path(raw))
    try:
        from app.shell.xcagi_mods_discover import mods_dir

        d = mods_dir()
        if d:
            roots.append(Path(d))
    except Exception:
        pass

    repo_mods = Path(__file__).resolve().parents[2] / "mods"
    roots.extend([repo_mods, Path.cwd() / "mods"])

    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        trial = root / PLANNER_FACADE_MOD_ID
        if (trial / "manifest.json").is_file():
            return trial
    return None


def _read_planner_manifest() -> dict[str, Any]:
    mod_dir = _resolve_planner_mod_dir()
    if not mod_dir:
        return {}
    try:
        data = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.debug("read planner manifest failed", exc_info=True)
        return {}


def is_planner_mod_on_disk() -> bool:
    return _resolve_planner_mod_dir() is not None


def is_planner_mod_installed() -> bool:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

        if is_mods_disabled():
            return False
    except Exception:
        pass
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        for row in get_mod_manager().list_all_mods():
            if str(row.get("id") or "").strip() == PLANNER_FACADE_MOD_ID:
                return True
    except Exception:
        logger.debug("list_all_mods for planner failed", exc_info=True)
    return is_planner_mod_on_disk()


def _manifest_tools_execution_enabled() -> bool:
    cfg = _read_planner_manifest().get("config") or {}
    if not isinstance(cfg, dict):
        return False
    if cfg.get("planner_tools_execution") is True:
        return True
    tools_cfg = cfg.get("planner_tools") or {}
    if isinstance(tools_cfg, dict) and tools_cfg.get("execution_via_mod_facade") is True:
        return True
    return False


def is_planner_tools_via_mod_enabled() -> bool:
    """对话与工具执行是否经 Mod 门面（默认：已安装且 manifest 声明）。"""
    if _truthy_env("XCAGI_DISABLE_PLANNER_MOD_TOOLS"):
        return False
    if _truthy_env("XCAGI_PLANNER_TOOLS_VIA_MOD"):
        return True
    if not is_planner_mod_installed():
        return False
    return _manifest_tools_execution_enabled()


def load_planner_tools_config() -> dict[str, Any]:
    mod_dir = _resolve_planner_mod_dir()
    if not mod_dir:
        return {}
    cfg_path = mod_dir / "config" / "planner_tools.json"
    if not cfg_path.is_file():
        return {}
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.warning("planner_tools.json parse failed: %s", cfg_path)
        return {}


def load_mod_planner_tool_extensions() -> list[dict[str, Any]]:
    """manifest.config.planner_tool_extensions 或 config/planner_tool_extensions.json。"""
    manifest = _read_planner_manifest()
    cfg = manifest.get("config") or {}
    inline = cfg.get("planner_tool_extensions") if isinstance(cfg, dict) else None
    if isinstance(inline, list):
        return [x for x in inline if isinstance(x, dict)]

    mod_dir = _resolve_planner_mod_dir()
    if not mod_dir:
        return []
    ext_path = mod_dir / "config" / "planner_tool_extensions.json"
    if not ext_path.is_file():
        return []
    try:
        data = json.loads(ext_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict) and isinstance(data.get("tools"), list):
            return [x for x in data["tools"] if isinstance(x, dict)]
    except Exception:
        logger.warning("planner_tool_extensions.json parse failed")
    return []


def get_planner_chat_tool_registry() -> list[dict[str, Any]]:
    from app.application.tools.workflow import get_workflow_tool_registry

    reg = list(get_workflow_tool_registry())
    extensions = load_mod_planner_tool_extensions()
    if extensions:
        reg = reg + extensions
    return reg


def resolve_planner_tool_executor() -> ExecuteToolFn:
    if is_planner_tools_via_mod_enabled():
        return execute_planner_workflow_tool
    from app.application.tools.workflow import execute_workflow_tool

    return execute_workflow_tool


def execute_planner_workflow_tool(
    name: str,
    args: dict[str, Any] | str,
    workspace_root: str | None = None,
    *,
    db_write_token: str | None = None,
) -> str:
    """里程碑 F：优先 Mod 原生 handler，其余委托宿主 workflow。"""
    from app.mod_sdk.planner_native_tools import try_execute_native_planner_tool

    native_raw, native_mod = try_execute_native_planner_tool(
        name,
        args,
        workspace_root,
        db_write_token=db_write_token,
    )
    if native_raw is not None:
        logger.debug("planner tool native mod=%s tool=%s", native_mod, name)
        return native_raw

    from app.application.tools.workflow import execute_workflow_tool

    raw = execute_workflow_tool(
        name,
        args,
        workspace_root,
        db_write_token=db_write_token,
    )
    if is_planner_tools_via_mod_enabled():
        logger.debug(
            "planner tool via mod facade: mod=%s tool=%s delegate=host.workflow",
            PLANNER_FACADE_MOD_ID,
            name,
        )
    return raw


def execute_planner_tool_from_body(body: dict[str, Any] | None) -> dict[str, Any]:
    payload = body or {}
    name = str(payload.get("tool_name") or payload.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "tool_name required"}

    args = payload.get("arguments") or payload.get("args") or {}
    workspace_root = str(
        payload.get("workspace_root") or os.environ.get("WORKSPACE_ROOT") or os.getcwd()
    ).strip()
    db_write_token = payload.get("db_write_token")
    if db_write_token is not None:
        db_write_token = str(db_write_token)

    try:
        raw = resolve_planner_tool_executor()(
            name,
            args,
            workspace_root,
            db_write_token=db_write_token,
        )
    except Exception as exc:
        logger.exception("planner tool execute failed: %s", name)
        return {"ok": False, "error": str(exc), "tool_name": name}

    execution_path = "host.workflow"
    handler_mod: str | None = None
    try:
        probe = json.loads(raw)
        if isinstance(probe, dict):
            src = str(probe.get("source") or "")
            if src.startswith("mod:"):
                execution_path = "mod_native"
                handler_mod = src.split(":", 1)[1] if ":" in src else None
    except json.JSONDecodeError:
        pass
    if execution_path == "host.workflow" and is_planner_tools_via_mod_enabled():
        execution_path = "mod_facade"
        handler_mod = PLANNER_FACADE_MOD_ID

    return {
        "ok": True,
        "tool_name": name,
        "result": raw,
        "execution_path": execution_path,
        "mod_id": handler_mod,
        "delegate": "host.workflow" if execution_path != "mod_native" else None,
    }


def list_planner_tools_registry_detail() -> dict[str, Any]:
    reg = get_planner_chat_tool_registry()
    names: list[str] = []
    for item in reg:
        fn = item.get("function") if isinstance(item, dict) else None
        if isinstance(fn, dict) and fn.get("name"):
            names.append(str(fn["name"]))

    extensions = load_mod_planner_tool_extensions()
    ext_names = []
    for item in extensions:
        fn = item.get("function") if isinstance(item, dict) else None
        if isinstance(fn, dict) and fn.get("name"):
            ext_names.append(str(fn["name"]))

    via_mod = is_planner_tools_via_mod_enabled()
    tools_cfg = load_planner_tools_config()
    from app.mod_sdk.planner_native_tools import list_native_planner_tools_summary

    native_summary = list_native_planner_tools_summary()
    return {
        "ok": True,
        "tool_count": len(names),
        "tool_names": names,
        "mod_extension_count": len(ext_names),
        "mod_extension_names": ext_names,
        "execution_via_mod_facade": via_mod,
        "native_planner_tools": native_summary,
        "execution_path": (
            "mod_facade+native"
            if via_mod and native_summary.get("enabled")
            else (
                "mod_native"
                if native_summary.get("enabled")
                else ("mod_facade" if via_mod else "host.workflow")
            )
        ),
        "mod_id": PLANNER_FACADE_MOD_ID if via_mod else None,
        "tools_execute_endpoint": (
            f"/api/mod/{PLANNER_FACADE_MOD_ID}/tools/execute" if via_mod else None
        ),
        "source": "mod_sdk.planner_tools" if via_mod else "host.workflow_tool_registry",
        "delegate": "host.workflow",
        "planner_tools_config": tools_cfg.get("execution") if tools_cfg else {},
        "note": (
            "里程碑 F3：Planner Excel/文档工具可由 xcagi-planner-excel-tools 原生执行（见 manifest native_planner_tools）。"
            if native_summary.get("tool_names")
            else (
                "里程碑 B：注册表与执行入口经 Mod 门面；handler 仍委托宿主 workflow。"
                if via_mod
                else "未启用 Mod 工具门面；安装 xcagi-planner-bridge 且 planner_tools_execution=true。"
            )
        ),
    }


__all__ = [
    "PLANNER_FACADE_MOD_ID",
    "execute_planner_tool_from_body",
    "execute_planner_workflow_tool",
    "get_planner_chat_tool_registry",
    "is_planner_mod_installed",
    "is_planner_tools_via_mod_enabled",
    "list_planner_tools_registry_detail",
    "load_mod_planner_tool_extensions",
    "load_planner_tools_config",
    "resolve_planner_tool_executor",
]
