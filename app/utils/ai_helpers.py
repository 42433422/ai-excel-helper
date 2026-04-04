# -*- coding: utf-8 -*-
"""
AI 聊天辅助工具函数

从 ai_chat.py 中提取的纯函数：
- 模式判断
- 数值处理
- 金额格式化
- 普通模式消息路由
"""

import re
from typing import Any, Dict, Optional


def is_pro_source(source: Optional[str]) -> bool:
    """判断是否为专业模式来源（pro/pro_mode/promode）"""
    normalized = str(source or "").strip().lower().replace("-", "_")
    return normalized in {"pro", "pro_mode", "promode"}

def is_qclaw_source(source: Optional[str]) -> bool:
    """判断是否为 Qclaw 生态来源。"""
    normalized = str(source or "").strip().lower().replace("-", "_")
    return normalized in {"qclaw", "qclaw_lobster", "lobster"}


def is_professional_mode(mode: Optional[str]) -> bool:
    """判断是否为专业模式"""
    normalized = str(mode or "").strip().lower().replace("-", "_")
    return normalized in {"professional", "pro", "pro_mode"}


def safe_float(value) -> Optional[float]:
    """安全转换为 float，失败返回 None"""
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if not value:
                return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_money(value: Optional[float]) -> str:
    """格式化金额为字符串"""
    if value is None:
        return "-"
    return f"{value:.2f}"


def route_normal_mode_message(message: str) -> Dict[str, Any]:
    """
    普通版轻量槽位提取与任务分流：
    - shipment: 发货单/开单/打印等单据语境
    - product_query: 产品检索语境（如“查询七彩乐园的9803”）
    - unknown: 未命中
    """
    text = (message or "").strip()
    lower = text.lower()

    shipment_keywords = ("发货单", "送货单", "出货单", "开单", "打单", "打印")
    number_style_order = bool(
        re.search(
            r"(?:\d+|[一二两三四五六七八九十零〇]+)\s*桶\s*[0-9A-Za-z-]+\s*规格\s*\d+(?:\.\d+)?",
            text,
        )
    )

    if any(k in text for k in shipment_keywords) or number_style_order:
        return {"mode": "shipment", "confidence": 0.9}

    product_keywords = ("查询", "价格", "多少钱", "型号", "库存", "规格")
    if any(k in lower for k in product_keywords):
        return {"mode": "product_query", "confidence": 0.8}

    return {"mode": "unknown", "confidence": 0.3}
