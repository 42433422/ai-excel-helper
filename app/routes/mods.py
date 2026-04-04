"""
Mod System API
"""
import logging
from flask import Blueprint, current_app, jsonify, request
from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

logger = logging.getLogger(__name__)

bp = Blueprint("mods", __name__, url_prefix="/api/mods")

logger.info(f"Mods blueprint created with url_prefix: /api/mods")


def is_client_mods_off() -> bool:
    # 优先检查请求 Header（前端实时传递）
    if request.headers.get('X-Client-Mods-Off', '').strip() == '1':
        return True
    # 同时检查状态文件（持久化状态，后端启动时已读取）
    try:
        from app.routes.state import read_client_mods_off_state
        return read_client_mods_off_state()
    except Exception:
        return False


@bp.after_request
def apply_client_mods_off(response):
    if is_client_mods_off():
        response.headers['X-Client-Mods-Off'] = '1'
    return response


@bp.route("", methods=["GET"])
@bp.route("/", methods=["GET"])
def list_mods():
    if is_client_mods_off():
        return jsonify({
            "success": True,
            "data": [],
            "mods_disabled": True,
            "client_mods_off": True,
            "message": "前端已启用原版模式：后端返回空列表"
        })

    try:
        mod_manager = get_mod_manager()
        mod_manager.ensure_mods_loaded(current_app._get_current_object())
        disabled = is_mods_disabled()
        mods = mod_manager.list_loaded_mods()
        sorted_mods = sorted(mods, key=lambda m: not m.primary)
        payload = {
            "success": True,
            "data": [
                {
                    "id": m.id,
                    "name": m.name,
                    "version": m.version,
                    "author": m.author,
                    "description": m.description,
                    "menu": m.frontend_menu,
                    "comms_exports": m.comms_exports,
                    "primary": m.primary,
                    "workflow_employees": m.workflow_employees,
                }
                for m in sorted_mods
            ],
            "mods_disabled": disabled,
        }
        if disabled:
            payload["message"] = "XCAGI_DISABLE_MODS 已启用：未加载任何 Mod 扩展"
        return jsonify(payload)
    except Exception as e:
        logger.exception("list_mods failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# 静态子路径必须注册在 /<mod_id> 之前，否则会被当成 mod_id（如 routes、comms）
@bp.route("/routes", methods=["GET"])
def get_mod_routes():
    if is_client_mods_off():
        return jsonify({
            "success": True,
            "data": [],
            "client_mods_off": True
        })
    try:
        mod_manager = get_mod_manager()
        mod_manager.ensure_mods_loaded(current_app._get_current_object())
        mods = mod_manager.list_loaded_mods()
        routes = []
        for mod in mods:
            fr = mod.frontend_routes
            if isinstance(fr, str):
                frs = fr.strip()
            else:
                frs = (str(fr).strip() if fr is not None else "")
            if frs:
                routes.append({
                    "mod_id": mod.id,
                    "routes_path": f"mods/{mod.id}/{frs}"
                })
        return jsonify({
            "success": True,
            "data": routes
        })
    except Exception as e:
        logger.exception("get_mod_routes failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/comms/endpoints", methods=["GET"])
def list_comms_endpoints():
    """已注册的 Mod 间通信端点（调试用，不含实现细节）。"""
    if is_client_mods_off():
        return jsonify({"success": True, "data": [], "client_mods_off": True})
    try:
        from app.infrastructure.mods.comms import get_mod_comms

        return jsonify({"success": True, "data": get_mod_comms().list_endpoints()})
    except Exception as e:
        logger.exception("list_comms_endpoints failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/loading-status", methods=["GET"])
def get_loading_status():
    """获取 Mod 加载状态，用于启动页面判断是否可以进入"""
    if is_client_mods_off():
        return jsonify({
            "success": True,
            "data": {
                "ready": True,
                "mods_disabled": True,
                "client_mods_off": True,
                "mods_loaded": 0,
                "discovered_mod_ids": [],
                "load_mismatch": False,
                "partial_failure": False,
                "load_errors": [],
                "blueprint_errors": [],
                "manifest_errors": [],
                "mods": []
            }
        })
    try:
        mod_manager = get_mod_manager()
        mod_manager.ensure_mods_loaded(current_app._get_current_object())
        loaded_mods = mod_manager.list_loaded_mods()
        discovered = mod_manager.scan_mods()
        discovered_ids = [m.id for m in discovered]

        sorted_mods = sorted(loaded_mods, key=lambda m: not m.primary)
        mods_off = is_mods_disabled()
        # 磁盘上有 Mod 但一个都没进注册表：前端可提示看后端日志 / XCAGI_MODS_ROOT（排除「主动关闭扩展」）
        load_mismatch = (not mods_off) and len(discovered_ids) > 0 and len(loaded_mods) == 0
        load_errors = mod_manager.get_recent_load_failures()
        blueprint_errors = mod_manager.get_blueprint_failures()
        manifest_errors = mod_manager.get_scan_manifest_errors()
        # 部分失败：扫描到的 mod 数多于已成功加载数（便于前端提示，不单独用于阻塞 ready）
        partial_failure = (not mods_off) and len(discovered_ids) > 0 and len(loaded_mods) < len(
            discovered_ids
        )

        return jsonify({
            "success": True,
            "data": {
                "ready": not load_mismatch,
                "mods_disabled": mods_off,
                "mods_loaded": len(loaded_mods),
                "mods_root": mod_manager.mods_root,
                "discovered_mod_ids": discovered_ids,
                "load_mismatch": load_mismatch,
                "partial_failure": partial_failure,
                "load_errors": load_errors,
                "blueprint_errors": blueprint_errors,
                "manifest_errors": manifest_errors,
                "mods": [
                    {"id": m.id, "name": m.name, "version": m.version}
                    for m in sorted_mods
                ]
            }
        })
    except Exception as e:
        logger.exception("get_loading_status failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/<mod_id>", methods=["GET"])
def get_mod(mod_id):
    if is_client_mods_off():
        return jsonify({"success": False, "error": "Mod not found", "client_mods_off": True}), 404
    try:
        mod_manager = get_mod_manager()
        mod_manager.ensure_mods_loaded(current_app._get_current_object())
        mod = mod_manager.get_mod(mod_id)
        if not mod:
            return jsonify({"success": False, "error": "Mod not found"}), 404

        return jsonify({
            "success": True,
            "data": {
                "id": mod.id,
                "name": mod.name,
                "version": mod.version,
                "author": mod.author,
                "description": mod.description,
                "menu": mod.frontend_menu,
                "comms_exports": mod.comms_exports,
            }
        })
    except Exception as e:
        logger.exception("get_mod failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
