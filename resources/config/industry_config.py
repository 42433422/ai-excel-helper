# -*- coding: utf-8 -*-
"""
行业配置管理

提供通用业务抽象，支持多行业配置切换
默认保留涂料行业实现，可扩展更多行业
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "industry_config.yaml"

_industry_config: Optional[Dict[str, Any]] = None
_config_mtime: float = 0


@dataclass
class UnitDefinition:
    """单位定义"""
    name: str           # 显示名称：如"桶"、"件"
    abbr: str          # 缩写：如"t"、"p"
    conversion_factor: float = 1.0  # 转换为标准单位的因子
    secondary_unit: Optional[str] = None  # 辅助单位


@dataclass
class QuantityFieldMapping:
    """数量字段映射"""
    primary_field: str           # 主字段名：tins, pieces, boxes
    secondary_field: str         # 辅助字段：kg, weight, cartons
    spec_field: str             # 规格字段：spec_per_tin, spec_per_box
    primary_label: str           # 主字段标签：桶数、件数
    secondary_label: str         # 辅助字段标签：公斤、重量
    spec_label: str              # 规格标签：规格、规格


@dataclass
class ProductFieldMapping:
    """产品字段映射"""
    name: str = "name"           # 产品名称字段
    model: str = "model_number"  # 型号字段
    category: str = "category"   # 分类字段
    price: str = "price"         # 价格字段
    unit: str = "unit"           # 单位字段


@dataclass
class OrderTypeMapping:
    """单据类型映射"""
    shipment: str = "发货单"     # 出库/销售单
    receipt: str = "收货单"      # 采购/入库单
    return_order: str = "退货单" # 退货单
    transfer: str = "调拨单"     # 调拨单


@dataclass
class IndustryProfile:
    """行业配置Profile"""
    id: str
    name: str
    units: Dict[str, Any]
    quantity_fields: Dict[str, str]
    product_fields: Dict[str, str]
    order_types: Dict[str, str]
    intent_keywords: Dict[str, List[str]]
    print_config: Dict[str, Any]

    @classmethod
    def from_dict(cls, industry_id: str, data: Dict[str, Any]) -> "IndustryProfile":
        return cls(
            id=industry_id,
            name=data.get("name", industry_id),
            units=data.get("units", {}),
            quantity_fields=data.get("quantity_fields", {}),
            product_fields=data.get("product_fields", {}),
            order_types=data.get("order_types", {}),
            intent_keywords=data.get("intent_keywords", {}),
            print_config=data.get("print_config", {}),
        )


def _load_config() -> Dict[str, Any]:
    """加载行业配置文件"""
    global _industry_config, _config_mtime

    if not CONFIG_FILE.exists():
        logger.warning(f"行业配置文件不存在: {CONFIG_FILE}，使用默认涂料配置")
        return _get_default_config()

    current_mtime = CONFIG_FILE.stat().st_mtime
    if _industry_config is None or current_mtime > _config_mtime:
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                _industry_config = yaml.safe_load(f)
            _config_mtime = current_mtime
            logger.info(f"行业配置已加载: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"加载行业配置失败: {e}")
            _industry_config = _get_default_config()

    return _industry_config or _get_default_config()


def _get_default_config() -> Dict[str, Any]:
    """获取默认配置（涂料行业）"""
    return {
        "default_industry": "涂料",
        "industries": {
            "涂料": {
                "name": "涂料/油漆行业",
                "description": "适用于涂料、油漆、固化剂等化工产品",
                "units": {
                    "primary": "桶",
                    "secondary": "kg",
                    "primary_label": "桶数",
                    "secondary_label": "公斤",
                    "spec_label": "规格",
                    "conversion": {
                        "桶_to_kg": 20.0,  # 1桶 = 20kg
                    }
                },
                "quantity_fields": {
                    "primary_field": "tins",
                    "secondary_field": "kg",
                    "spec_field": "spec_per_tin",
                    "primary_label": "桶数",
                    "secondary_label": "公斤",
                    "spec_label": "规格"
                },
                "product_fields": {
                    "name": "产品名称",
                    "model": "型号",
                    "category": "产品类型",
                    "price": "单价",
                    "unit": "单位"
                },
                "order_types": {
                    "shipment": "发货单",
                    "receipt": "收货单",
                    "return": "退货单"
                },
                "intent_keywords": {
                    "create_order": ["开发货单", "生成发货单", "做发货单", "开单", "打单", "做出货单"],
                    "quantity_unit": "桶",
                    "print_label": ["商标", "标签", "打印标签"]
                },
                "print_config": {
                    "printer_type": "TSC",
                    "label_width": 60,
                    "label_height": 40
                }
            },
            "电商": {
                "name": "电商/零售行业",
                "description": "适用于电商、零售、批发等商品销售",
                "units": {
                    "primary": "件",
                    "secondary": "箱",
                    "primary_label": "件数",
                    "secondary_label": "箱数",
                    "spec_label": "规格",
                    "conversion": {
                        "箱_to_件": 12.0,  # 1箱 = 12件
                    }
                },
                "quantity_fields": {
                    "primary_field": "pieces",
                    "secondary_field": "cartons",
                    "spec_field": "spec_per_box",
                    "primary_label": "件数",
                    "secondary_label": "箱数",
                    "spec_label": "规格"
                },
                "product_fields": {
                    "name": "商品名称",
                    "model": "SKU",
                    "category": "分类",
                    "price": "售价",
                    "unit": "单位"
                },
                "order_types": {
                    "shipment": "销售单",
                    "receipt": "采购单",
                    "return": "退货单"
                },
                "intent_keywords": {
                    "create_order": ["开销售单", "创建订单", "下单", "开单"],
                    "quantity_unit": "件",
                    "print_label": ["面单", "快递单", "标签"]
                },
                "print_config": {
                    "printer_type": "PDF",
                    "label_width": 100,
                    "label_height": 50
                }
            },
            "餐饮": {
                "name": "餐饮/食品行业",
                "description": "适用于餐饮、食品加工、原材料采购",
                "units": {
                    "primary": "斤",
                    "secondary": "公斤",
                    "primary_label": "斤数",
                    "secondary_label": "公斤",
                    "spec_label": "规格",
                    "conversion": {
                        "公斤_to_斤": 2.0,  # 1kg = 2斤
                    }
                },
                "quantity_fields": {
                    "primary_field": "jin",
                    "secondary_field": "kg",
                    "spec_field": "spec_per_jin",
                    "primary_label": "斤数",
                    "secondary_label": "公斤",
                    "spec_label": "规格"
                },
                "product_fields": {
                    "name": "食材名称",
                    "model": "编号",
                    "category": "类别",
                    "price": "单价",
                    "unit": "单位"
                },
                "order_types": {
                    "shipment": "领料单",
                    "receipt": "采购单",
                    "return": "退货单"
                },
                "intent_keywords": {
                    "create_order": ["开领料单", "领料", "申请食材"],
                    "quantity_unit": "斤",
                    "print_label": ["标签", "食材标签"]
                },
                "print_config": {
                    "printer_type": "PDF",
                    "label_width": 60,
                    "label_height": 40
                }
            }
        }
    }


def get_industry_config() -> Dict[str, Any]:
    """获取行业配置"""
    return _load_config()


def get_available_industries() -> List[Dict[str, str]]:
    """获取可用行业列表"""
    config = _load_config()
    industries = config.get("industries", {})
    return [
        {"id": industry_id, "name": data.get("name", industry_id)}
        for industry_id, data in industries.items()
    ]


def get_industry_profile(industry_id: Optional[str] = None) -> IndustryProfile:
    """获取指定行业配置"""
    config = _load_config()
    industries = config.get("industries", {})

    if industry_id is None:
        industry_id = config.get("default_industry", "涂料")

    industry_data = industries.get(industry_id)
    if industry_data is None:
        logger.warning(f"未找到行业配置: {industry_id}，使用默认涂料配置")
        industry_id = "涂料"
        industry_data = industries.get(industry_id, {})

    return IndustryProfile.from_dict(industry_id, industry_data)


def get_current_industry() -> str:
    """获取当前行业ID"""
    config = _load_config()
    return config.get("default_industry", "涂料")


def set_current_industry(industry_id: str) -> bool:
    """设置当前行业（仅修改运行时状态，不持久化）"""
    global _industry_config
    config = _load_config()
    industries = config.get("industries", {})

    if industry_id not in industries:
        logger.error(f"无法设置未知行业: {industry_id}")
        return False

    config["default_industry"] = industry_id
    _industry_config = config
    logger.info(f"当前行业已切换为: {industry_id}")
    return True


def get_unit_info(industry_id: Optional[str] = None) -> Dict[str, Any]:
    """获取行业单位配置"""
    profile = get_industry_profile(industry_id)
    return profile.units


def get_quantity_field_labels(industry_id: Optional[str] = None) -> Dict[str, str]:
    """获取数量字段标签"""
    profile = get_industry_profile(industry_id)
    return {
        "primary": profile.quantity_fields.get("primary_label", "数量"),
        "secondary": profile.quantity_fields.get("secondary_label", "重量"),
        "spec": profile.quantity_fields.get("spec_label", "规格"),
    }


def get_intent_keywords(industry_id: Optional[str] = None) -> Dict[str, Any]:
    """获取行业意图关键词"""
    profile = get_industry_profile(industry_id)
    return profile.intent_keywords


def reload_industry_config() -> Dict[str, Any]:
    """强制重新加载配置"""
    global _industry_config, _config_mtime
    _industry_config = None
    _config_mtime = 0
    return _load_config()


_industry_config: Optional[Dict[str, Any]] = None


def save_industry_config(config: Dict[str, Any]) -> bool:
    """保存行业配置到文件"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        reload_industry_config()
        return True
    except Exception as e:
        logger.error(f"保存行业配置失败: {e}")
        return False
