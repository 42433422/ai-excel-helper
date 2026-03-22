# -*- coding: utf-8 -*-
"""
系统设置 API

提供行业配置、系统配置等 API
"""

from flask import Blueprint, jsonify, request

system_bp = Blueprint('system', __name__)


@system_bp.route('/api/system/industries', methods=['GET'])
def get_industries():
    """获取可用行业列表"""
    try:
        from resources.config.industry_config import get_available_industries, get_current_industry

        industries = get_available_industries()
        current = get_current_industry()

        return jsonify({
            "success": True,
            "data": {
                "industries": industries,
                "current": current
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@system_bp.route('/api/system/industry', methods=['GET'])
def get_current_industry_info():
    """获取当前行业详细信息"""
    try:
        from resources.config.industry_config import get_current_industry, get_industry_profile

        current = get_current_industry()
        profile = get_industry_profile(current)

        return jsonify({
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
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@system_bp.route('/api/system/industry', methods=['POST'])
def set_industry():
    """设置当前行业"""
    try:
        from app.domain.value_objects_industry import set_current_industry as set_vo_industry
        from resources.config.industry_config import set_current_industry as set_industry_config

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

        ok = set_industry_config(industry_id)
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
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@system_bp.route('/api/system/industry/<industry_id>', methods=['GET'])
def get_industry_detail(industry_id):
    """获取指定行业详细信息"""
    try:
        from resources.config.industry_config import get_industry_profile

        profile = get_industry_profile(industry_id)

        return jsonify({
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
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@system_bp.route('/api/system/config', methods=['GET'])
def get_system_config():
    """获取系统配置"""
    try:
        from resources.config.industry_config import get_available_industries, get_current_industry

        return jsonify({
            "success": True,
            "data": {
                "current_industry": get_current_industry(),
                "available_industries": get_available_industries(),
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
