# -*- coding: utf-8 -*-
"""
值对象行业配置访问层

为 value_objects 提供行业配置的轻量级访问
避免循环导入问题
"""

from typing import Any, Dict, Optional

_current_industry: str = "涂料"

_industry_units_cache: Dict[str, Dict[str, Any]] = {}

_industry_fields_cache: Dict[str, Dict[str, str]] = {}


def _load_from_yaml():
    """从 YAML 配置加载行业配置"""
    global _industry_units_cache, _industry_fields_cache, _current_industry

    try:
        from resources.config.industry_config import _load_config
        config = _load_config()
        industries = config.get("industries", {})
        default_ind = config.get("default_industry", "涂料")

        _industry_units_cache = {}
        _industry_fields_cache = {}

        for ind_id, ind_data in industries.items():
            units = ind_data.get("units", {})
            qty_fields = ind_data.get("quantity_fields", {})

            _industry_units_cache[ind_id] = units
            _industry_fields_cache[ind_id] = qty_fields

        _current_industry = default_ind
    except Exception:
        _industry_units_cache = {
            "涂料": {
                "primary": "桶",
                "secondary": "kg",
                "primary_label": "桶数",
                "secondary_label": "公斤",
                "spec_label": "规格",
                "primary_field": "tins",
                "secondary_field": "kg",
                "spec_field": "spec_per_tin",
                "conversion": {
                    "桶_to_kg": 20.0,
                }
            }
        }
        _industry_fields_cache = {
            "涂料": {
                "primary_field": "tins",
                "secondary_field": "kg",
                "spec_field": "spec_per_tin",
            }
        }


_load_from_yaml()


def get_current_industry() -> str:
    """获取当前行业ID"""
    return _current_industry


def set_current_industry(industry_id: str) -> bool:
    """设置当前行业"""
    global _current_industry
    if industry_id in _industry_units_cache:
        _current_industry = industry_id
        return True
    return False


def get_current_industry_config() -> Dict[str, Any]:
    """获取当前行业的完整单位配置"""
    return _industry_units_cache.get(_current_industry, _industry_units_cache.get("涂料", {}))


def get_current_industry_fields() -> Dict[str, str]:
    """获取当前行业的字段配置"""
    return _industry_fields_cache.get(_current_industry, _industry_fields_cache.get("涂料", {}))


def register_industry_units(industry_id: str, units_config: Dict[str, Any], fields_config: Dict[str, str]) -> None:
    """注册行业配置"""
    _industry_units_cache[industry_id] = units_config
    _industry_fields_cache[industry_id] = fields_config


def get_primary_field_name() -> str:
    """获取当前行业的主数量字段名"""
    fields = get_current_industry_fields()
    return fields.get("primary_field", "tins")


def get_secondary_field_name() -> str:
    """获取当前行业的辅助数量字段名"""
    fields = get_current_industry_fields()
    return fields.get("secondary_field", "kg")


def get_spec_field_name() -> str:
    """获取当前行业的规格字段名"""
    fields = get_current_industry_fields()
    return fields.get("spec_field", "spec_per_tin")


def reload_config():
    """重新加载配置"""
    global _industry_units_cache, _industry_fields_cache
    _load_from_yaml()
