"""
Mods API Routes - FastAPI Implementation

Provides endpoints for:
- GET /api/mods/ - List all mods
- GET /api/mods/loading-status - Get mod loading status
- GET /api/mods/routes - Get mod routes
"""

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = None


def get_mods_router() -> Any:
    global router
    if router is None:
        from fastapi import APIRouter

        router = APIRouter(prefix="/api/mods", tags=["mods"])
        _register_mods_endpoints(router)
    return router


def _register_mods_endpoints(router) -> None:
    @router.get("/loading-status")
    async def get_loading_status():
        """Get mod loading status - returns discovered mods, load errors, etc."""
        try:
            from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

            if is_mods_disabled():
                return {
                    "success": True,
                    "data": {
                        "discovered_mod_ids": [],
                        "primary_mod_id": None,
                        "primary_mod_count": 0,
                        "mods_loaded": 0,
                        "load_mismatch": False,
                        "load_errors": [],
                        "manifest_errors": [],
                        "blueprint_errors": [],
                        "partial_failure": False,
                        "mods_disabled": True,
                    },
                }

            mm = get_mod_manager()
            mm._refresh_mods_root_if_needed()

            scanned = mm.scan_mods()
            discovered_mod_ids = [m.id for m in scanned if m.id]

            loaded_mods = mm.list_loaded_mods()
            mods_loaded = len(loaded_mods)

            primary_mods = [m for m in scanned if m.primary and m.id]
            primary_mod_id = primary_mods[0].id if len(primary_mods) == 1 else None
            primary_mod_count = len(primary_mods)

            load_mismatch = len(scanned) > 0 and mods_loaded == 0

            manifest_errors = [
                {"mod_id": e.get("mod_id", "unknown"), "error": e.get("error", str(e))}
                for e in mm._scan_manifest_errors
            ]

            blueprint_errors = [
                {"mod_id": e.get("mod_id", "unknown"), "error": e.get("error", str(e))}
                for e in mm._blueprint_failures
            ]

            load_errors = [
                {"mod_id": e.get("mod_id", "unknown"), "error": e.get("error", str(e))}
                for e in mm._recent_load_failures
            ]

            partial_failure = len(load_errors) > 0 or len(blueprint_errors) > 0

            return {
                "success": True,
                "data": {
                    "discovered_mod_ids": discovered_mod_ids,
                    "primary_mod_id": primary_mod_id,
                    "primary_mod_count": primary_mod_count,
                    "mods_loaded": mods_loaded,
                    "load_mismatch": load_mismatch,
                    "load_errors": load_errors,
                    "manifest_errors": manifest_errors,
                    "blueprint_errors": blueprint_errors,
                    "partial_failure": partial_failure,
                    "mods_disabled": False,
                },
            }
        except Exception as e:
            logger.exception(f"get_loading_status failed: {e}")
            return {
                "success": True,
                "data": {
                    "discovered_mod_ids": [],
                    "primary_mod_id": None,
                    "primary_mod_count": 0,
                    "mods_loaded": 0,
                    "load_mismatch": False,
                    "load_errors": [{"mod_id": "unknown", "error": str(e)}],
                    "manifest_errors": [],
                    "blueprint_errors": [],
                    "partial_failure": True,
                    "mods_disabled": False,
                    "error": str(e),
                },
            }

    @router.get("/")
    async def list_mods(all: str | None = None):
        """List all loaded or discovered mods

        Args:
            all: 当传入 "1" 时，返回磁盘扫描的全部 Mod 列表（不受已加载状态影响）
        """
        try:
            from app.infrastructure.mods.mod_manager import get_mod_manager

            mm = get_mod_manager()
            # 侧栏菜单/图标需要实时反映 manifest 变更，默认也走磁盘扫描。
            # 保留 ?all=1 兼容旧调用方；当前两者行为一致。
            mods = mm.list_all_mods()
            return {"success": True, "data": mods}
        except Exception as e:
            logger.exception(f"list_mods failed: {e}")
            return {"success": False, "message": str(e), "data": []}

    @router.get("/routes")
    async def list_routes():
        """Get mod routes for frontend registration"""
        try:
            from app.infrastructure.mods.mod_manager import get_mod_manager

            mm = get_mod_manager()
            routes = mm.get_routes()
            return {"success": True, "data": routes}
        except Exception as e:
            logger.exception(f"list_routes failed: {e}")
            return {"success": False, "message": str(e), "data": []}

    @router.get("/comms/endpoints")
    async def list_comms_endpoints():
        """已注册的 Mod 间通信端点（与归档 ``/api/mods/comms/endpoints`` 对齐）。"""
        try:
            from app.infrastructure.mods.comms import get_mod_comms

            return {"success": True, "data": get_mod_comms().list_endpoints()}
        except Exception as e:
            logger.exception("list_comms_endpoints failed: %s", e)
            return {"success": False, "error": str(e)}

    @router.get("/employee-packs/{pack_id}/config-preview")
    async def employee_pack_config_preview(pack_id: str):
        """返回已安装 employee_pack 的 ``employee_config_v2`` 摘要（供宿主/MODstore 联调）。"""
        import json
        import os

        try:
            from app.infrastructure.mods.mod_manager import _default_mods_root
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": str(e)}
        root = os.path.join(_default_mods_root(), "_employees", (pack_id or "").strip(), "manifest.json")
        if not os.path.isfile(root):
            return {"success": False, "error": "员工包未安装或 manifest 不存在"}
        try:
            with open(root, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            return {"success": False, "error": str(e)}
        v2 = data.get("employee_config_v2")
        hp = data.get("xcagi_host_profile")
        cog = (v2 or {}).get("cognition") if isinstance(v2, dict) else {}
        agent = cog.get("agent") if isinstance(cog, dict) else {}
        model = agent.get("model") if isinstance(agent, dict) else {}
        return {
            "success": True,
            "data": {
                "pack_id": data.get("id") or pack_id,
                "has_employee_config_v2": isinstance(v2, dict),
                "cognition_model": model if isinstance(model, dict) else {},
                "system_prompt_preview": (
                    str(agent.get("system_prompt") or "")[:400] if isinstance(agent, dict) else ""
                ),
                "xcagi_host_profile": hp if isinstance(hp, dict) else None,
            },
        }

    @router.get("/{mod_id}")
    async def get_mod_detail(mod_id: str, request: Request):
        """单个 Mod 元数据（须注册在 ``/comms``、``/routes`` 等静态段之后）。"""
        try:
            from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

            if is_mods_disabled():
                return JSONResponse({"success": False, "error": "Mod not found"}, status_code=404)

            mm = get_mod_manager()
            mm.ensure_mods_loaded(request.app)
            mod = mm.get_mod(mod_id)
            if not mod:
                return JSONResponse({"success": False, "error": "Mod not found"}, status_code=404)

            return {
                "success": True,
                "data": {
                    "id": mod.id,
                    "name": mod.name,
                    "version": mod.version,
                    "author": mod.author,
                    "description": mod.description,
                    "menu": mod.frontend_menu,
                    "menu_overrides": mod.frontend_menu_overrides,
                    "comms_exports": mod.comms_exports,
                },
            }
        except Exception as e:
            logger.exception("get_mod_detail failed: %s", e)
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
