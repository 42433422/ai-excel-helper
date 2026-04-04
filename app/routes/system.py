# -*- coding: utf-8 -*-
"""
系统设置 API

提供行业配置、系统配置等 API
"""

import logging
import sys
from pathlib import Path

from flask import Blueprint, jsonify, request

from app.utils.json_safe import json_safe

logger = logging.getLogger(__name__)

system_bp = Blueprint('system', __name__)

# app/routes/system.py -> parents[2] == XCAGI 项目根（含 resources/ 包）
_XCAGI_ROOT = Path(__file__).resolve().parents[2]


def _ensure_project_root_on_syspath() -> None:
    """保证可从任意工作目录启动时仍能 import resources.config.industry_config。"""
    root = str(_XCAGI_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _import_industry_config():
    _ensure_project_root_on_syspath()
    from resources.config import industry_config as ic

    return ic


def _json_response(payload: dict, status: int = 200):
    """jsonify + json_safe；极端情况下回退为最小 JSON，避免整页依赖接口裸 500。"""
    try:
        return jsonify(json_safe(payload)), status
    except Exception as e:
        logger.exception("system API: jsonify failed: %s", e)
        fallback = {
            "success": bool(payload.get("success", True)),
            "error": "响应序列化失败，请检查行业 YAML / Mod 覆盖是否含不可 JSON 化的对象",
            "data": payload.get("data"),
        }
        try:
            return jsonify(json_safe(fallback)), 500
        except Exception:
            return jsonify({"success": False, "error": str(e)}), 500


def _industries_degraded_payload(exc: BaseException) -> dict:
    logger.warning("industries API degraded after error: %s", exc)
    return {
        "success": True,
        "data": {
            "industries": [{"id": "涂料", "name": "涂料/油漆行业"}],
            "current": "涂料",
            "degraded": True,
            "hint": (str(exc) or "error")[:300],
        },
    }


@system_bp.route('/api/system/industries', methods=['GET'])
def get_industries():
    """获取可用行业列表"""
    try:
        ic = _import_industry_config()
        industries = ic.get_available_industries()
        current = ic.get_current_industry()
        return _json_response(
            {
                "success": True,
                "data": {
                    "industries": industries,
                    "current": current,
                },
            }
        )
    except Exception as e:
        logger.exception("get_industries failed: %s", e)
        return _json_response(_industries_degraded_payload(e), 200)


@system_bp.route('/api/system/industry', methods=['GET'])
def get_current_industry_info():
    """获取当前行业详细信息"""
    try:
        ic = _import_industry_config()
        current = ic.get_current_industry()
        profile = ic.get_industry_profile(current)
        return _json_response(
            {
                "success": True,
                "data": {
                    "id": profile.id,
                    "name": profile.name,
                    "units": profile.units,
                    "quantity_fields": profile.quantity_fields,
                    "product_fields": profile.product_fields,
                    "order_types": profile.order_types,
                    "intent_keywords": profile.intent_keywords,
                    "print_config": profile.print_config,
                },
            }
        )
    except Exception as e:
        logger.exception("get_current_industry_info failed: %s", e)
        return _json_response(
            {
                "success": True,
                "data": {
                    "id": "涂料",
                    "name": "涂料/油漆行业",
                    "units": {
                        "primary": "桶",
                        "secondary": "kg",
                        "primary_label": "桶数",
                        "secondary_label": "公斤",
                        "spec_label": "规格",
                    },
                    "quantity_fields": {},
                    "product_fields": {},
                    "order_types": {},
                    "intent_keywords": {},
                    "print_config": {},
                    "degraded": True,
                    "hint": (str(e) or "error")[:300],
                },
            },
            200,
        )


@system_bp.route('/api/system/industry', methods=['POST'])
def set_industry():
    """设置当前行业"""
    try:
        from app.domain.value_objects_industry import set_current_industry as set_vo_industry

        ic = _import_industry_config()

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({
                "success": False,
                "error": "无效的 JSON 数据"
            }), 400

        industry_id = data.get('industry_id')

        if not industry_id:
            return jsonify({
                "success": False,
                "error": "缺少 industry_id 参数"
            }), 400

        ok = ic.set_current_industry(industry_id)
        if ok:
            set_vo_industry(industry_id)
            return jsonify({
                "success": True,
                "message": f"已切换到 {industry_id} 行业"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"未知行业: {industry_id}"
            }), 400
    except Exception as e:
        logger.exception("set_industry failed: %s", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@system_bp.route('/api/system/industry/<industry_id>', methods=['GET'])
def get_industry_detail(industry_id):
    """获取指定行业详细信息"""
    try:
        ic = _import_industry_config()
        profile = ic.get_industry_profile(industry_id)
        return _json_response(
            {
                "success": True,
                "data": {
                    "id": profile.id,
                    "name": profile.name,
                    "units": profile.units,
                    "quantity_fields": profile.quantity_fields,
                    "product_fields": profile.product_fields,
                    "order_types": profile.order_types,
                    "intent_keywords": profile.intent_keywords,
                    "print_config": profile.print_config,
                },
            }
        )
    except Exception as e:
        logger.exception("get_industry_detail failed: %s", e)
        return _json_response(
            {
                "success": False,
                "error": str(e),
            },
            500,
        )


@system_bp.route('/api/system/config', methods=['GET'])
def get_system_config():
    """获取系统配置"""
    try:
        ic = _import_industry_config()
        return _json_response(
            {
                "success": True,
                "data": {
                    "current_industry": ic.get_current_industry(),
                    "available_industries": ic.get_available_industries(),
                },
            }
        )
    except Exception as e:
        logger.exception("get_system_config failed: %s", e)
        return _json_response(
            {
                "success": True,
                "data": {
                    "current_industry": "涂料",
                    "available_industries": [{"id": "涂料", "name": "涂料/油漆行业"}],
                    "degraded": True,
                    "hint": (str(e) or "error")[:300],
                },
            },
            200,
        )


@system_bp.route('/api/system/test-db/status', methods=['GET'])
def get_test_db_status():
    """获取测试数据库状态"""
    try:
        from app.db.test_db_manager import get_test_db_manager
        mgr = get_test_db_manager()
        return _json_response({
            "success": True,
            "data": mgr.get_status()
        })
    except Exception as e:
        logger.exception("get_test_db_status failed: %s", e)
        return _json_response({
            "success": False,
            "error": str(e)
        }, 500)


@system_bp.route('/api/system/test-db/enable', methods=['POST'])
def enable_test_db():
    """启用测试数据库模式"""
    try:
        from app.db.test_db_manager import get_test_db_manager
        from app.db import close_old_connections
        mgr = get_test_db_manager()
        result = mgr.enable()
        close_old_connections()
        return _json_response({
            "success": result["success"],
            "message": result.get("message"),
            "data": result
        })
    except Exception as e:
        logger.exception("enable_test_db failed: %s", e)
        return _json_response({
            "success": False,
            "error": str(e)
        }, 500)


@system_bp.route('/api/system/test-db/disable', methods=['POST'])
def disable_test_db():
    """停用测试数据库模式"""
    try:
        from app.db.test_db_manager import get_test_db_manager
        from app.db import close_old_connections
        mgr = get_test_db_manager()
        result = mgr.disable()
        close_old_connections()
        return _json_response({
            "success": result["success"],
            "message": result.get("message"),
            "data": result
        })
    except Exception as e:
        logger.exception("disable_test_db failed: %s", e)
        return _json_response({
            "success": False,
            "error": str(e)
        }, 500)
