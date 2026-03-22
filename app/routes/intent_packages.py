# -*- coding: utf-8 -*-
"""
意图包配置 API

管理不同行业的 AI 意图识别配置包
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request

intent_packages_bp = Blueprint('intent_packages', __name__)

_intent_packages_state: Dict[str, bool] = {
    "base": True,
    "industry": True,
    "product": True,
    "quantity": True,
    "customer": True,
}


@intent_packages_bp.route('/api/intent-packages', methods=['GET'])
def get_intent_packages():
    """获取所有意图包配置"""
    try:
        from resources.config.industry_config import get_current_industry, get_industry_profile

        current_industry = get_current_industry()
        profile = get_industry_profile(current_industry)

        industry_keywords = []
        kw_config = profile.intent_keywords
        if kw_config:
            create_kw = kw_config.get('create_order', [])
            if isinstance(create_kw, list):
                industry_keywords.extend(create_kw)
            else:
                industry_keywords.append(create_kw)

            qty_unit = kw_config.get('quantity_unit', '')
            if qty_unit:
                industry_keywords.append(qty_unit)

            print_kw = kw_config.get('print_label', [])
            if isinstance(print_kw, list):
                industry_keywords.extend(print_kw)
            elif print_kw:
                industry_keywords.append(print_kw)

        packages = {
            "base": {
                "id": "base",
                "name": "基础意图",
                "icon": "📋",
                "description": "通用的单据操作意图：创建、查询、修改、删除、打印",
                "enabled": _intent_packages_state.get("base", True),
                "keywords": ["开单", "查询", "打印", "导出", "删除", "修改", "创建", "生成"]
            },
            "industry": {
                "id": "industry",
                "name": "行业特定",
                "icon": "🏭",
                "description": f"当前行业（{profile.name}）的特定用语和业务词汇",
                "enabled": _intent_packages_state.get("industry", True),
                "keywords": list(set(industry_keywords))[:12]
            },
            "product": {
                "id": "product",
                "name": "产品识别",
                "icon": "📦",
                "description": "产品型号、规格、分类的识别和解析",
                "enabled": _intent_packages_state.get("product", True),
                "keywords": ["型号", "规格", "分类", "产品名", "编号"]
            },
            "quantity": {
                "id": "quantity",
                "name": "数量解析",
                "icon": "🔢",
                "description": "数量单位和中文数字的智能解析",
                "enabled": _intent_packages_state.get("quantity", True),
                "keywords": _get_quantity_keywords(current_industry)
            },
            "customer": {
                "id": "customer",
                "name": "客户识别",
                "icon": "👥",
                "description": "客户名称、联系方式、地址的识别",
                "enabled": _intent_packages_state.get("customer", True),
                "keywords": ["客户", "单位", "联系人", "地址", "电话"]
            }
        }

        return jsonify({
            "success": True,
            "data": {
                "packages": packages,
                "current_industry": current_industry
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@intent_packages_bp.route('/api/intent-packages', methods=['POST'])
def update_intent_packages():
    """更新意图包配置"""
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({
                "success": False,
                "error": "无效的 JSON 数据"
            }), 400

        package_states = data.get('packages', {})
        for pkg_id, state in package_states.items():
            if pkg_id in _intent_packages_state:
                _intent_packages_state[pkg_id] = bool(state)

        return jsonify({
            "success": True,
            "message": "意图包配置已更新",
            "data": {
                "packages": _intent_packages_state
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@intent_packages_bp.route('/api/intent-packages/<package_id>', methods=['PUT'])
def update_single_package(package_id):
    """更新单个意图包"""
    try:
        if package_id not in _intent_packages_state:
            return jsonify({
                "success": False,
                "error": f"未知的意图包: {package_id}"
            }), 404

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({
                "success": False,
                "error": "无效的 JSON 数据"
            }), 400

        enabled = data.get('enabled')
        if enabled is not None:
            _intent_packages_state[package_id] = bool(enabled)

        return jsonify({
            "success": True,
            "data": {
                "package_id": package_id,
                "enabled": _intent_packages_state[package_id]
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _get_quantity_keywords(industry_id: str) -> list:
    """根据行业获取数量单位关键词"""
    keywords_map = {
        "涂料": ["桶", "kg", "公斤", "升", "二十三", "一十", "十三"],
        "电商": ["件", "箱", "个", "套", "二十三", "一十", "十三"],
        "餐饮": ["斤", "公斤", "克", "份", "二十三", "一十", "十三"],
        "物流": ["件", "吨", "立方", "箱", "二十三", "一十", "十三"],
    }
    return keywords_map.get(industry_id, ["件", "箱", "个", "二十三", "一十", "十三"])


def is_package_enabled(package_id: str) -> bool:
    """检查意图包是否启用"""
    return _intent_packages_state.get(package_id, True)


def get_enabled_packages() -> Dict[str, bool]:
    """获取所有启用的意图包"""
    return _intent_packages_state.copy()
