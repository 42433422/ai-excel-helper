# -*- coding: utf-8 -*-
"""
普通版聊天槽位路由与产品查询响应（与 unified_chat 行为一致）。

供 /api/ai/unified_chat、工作流 execute_registered_workflow_tool（tool_execution_profile=normal）
及 normal_slot_dispatch 工具复用。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from app.utils.ai_helpers import format_money, safe_float

logger = logging.getLogger(__name__)


def route_normal_mode_message(message: str) -> Dict[str, Any]:
    """
    普通版轻量槽位提取与任务分流：
    - shipment: 发货单 / 开单 / 打印 / 出货单等单据语境
    - product_query: 产品库检索
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
        return {
            "intent": "shipment",
            "slots": {"number_style_order": number_style_order},
        }

    query_keywords = ("查询", "查一下", "查下", "查", "看看", "看下", "搜索", "找下", "找", "检索")
    model_signal = bool(re.search(r"(?:型号|编号)\s*[:：]?\s*([0-9A-Za-z-]{2,})", text))
    unit_model_signal = bool(re.search(r"([^\s，,。]{2,})\s*的\s*([0-9A-Za-z-]{2,})", text))
    if any(k in text for k in query_keywords) or model_signal or unit_model_signal:
        slots: Dict[str, Any] = {}

        m_unit_model = re.search(r"([^\s，,。]{2,})\s*的\s*([0-9A-Za-z-]{2,})", text)
        if m_unit_model:
            slots["unit_name"] = (m_unit_model.group(1) or "").strip()
            slots["model_number"] = (m_unit_model.group(2) or "").strip().upper()

        m_model = re.search(r"(?:型号|编号)\s*[:：]?\s*([0-9A-Za-z-]{2,})", text)
        if m_model and not slots.get("model_number"):
            slots["model_number"] = (m_model.group(1) or "").strip().upper()

        if slots.get("unit_name"):
            slots["unit_name"] = re.sub(
                r"^(?:帮我|给我|请)?\s*(?:查询|查一下|查下|查|看看|看下|搜索|找下|找|检索)(?:一下)?\s*",
                "",
                str(slots["unit_name"]),
                flags=re.IGNORECASE,
            ).strip()

        if not slots.get("model_number"):
            m_tail_model = re.search(r"\b([0-9A-Za-z-]{3,})\b", text)
            if m_tail_model:
                token = (m_tail_model.group(1) or "").strip().upper()
                if not re.fullmatch(r"(API|HTTP|JSON|XML)", token):
                    slots["model_number"] = token

        if not slots.get("keyword"):
            if slots.get("unit_name") and slots.get("model_number"):
                slots["keyword"] = f"{slots['unit_name']}{slots['model_number']}"
            elif slots.get("model_number"):
                tail = re.sub(
                    r"^(?:帮我|给我|请)?\s*(?:查询|查一下|查下|查|看看|看下|搜索|找下|找|检索)(?:一下)?\s*",
                    "",
                    text,
                ).strip()
                m_combo = re.search(r"([\u4e00-\u9fff]{2,})([0-9A-Za-z-]{2,})", tail)
                if m_combo:
                    slots["keyword"] = f"{m_combo.group(1).strip()}{m_combo.group(2).strip().upper()}"
                else:
                    slots["keyword"] = slots.get("model_number")
            else:
                keyword = re.sub(
                    r"(?:帮我|给我|请|查询|查一下|查下|查|看看|看下|搜索|找下|找|检索|一下|一下子)",
                    " ",
                    lower,
                )
                keyword = re.sub(r"\s+", " ", keyword).strip()
                if keyword:
                    slots["keyword"] = keyword

        return {"intent": "product_query", "slots": slots}

    return {"intent": "unknown", "slots": {}}


def build_product_query_response_dict(route_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """构造与 unified_chat 产品查询分支一致的响应 dict。"""
    if route_result.get("intent") != "product_query":
        return None

    route_slots = route_result.get("slots") or {}
    unit_name = str(route_slots.get("unit_name") or "").strip()
    model_number = str(route_slots.get("model_number") or "").strip().upper()
    keyword = str(route_slots.get("keyword") or "").strip()

    preview_lines = []
    preview_count = 0
    try:
        from app.bootstrap import get_products_service

        products_service = get_products_service()
        kw_preview = (keyword or "").strip() or (model_number or "").strip()
        result = products_service.get_products(
            unit_name=None,
            model_number=None,
            keyword=kw_preview or None,
            page=1,
            per_page=5,
        ) or {}
        rows = result.get("data") or []
        preview_count = len(rows)
        for row in rows[:3]:
            m = (row.get("model_number") or "").strip()
            n = (row.get("name") or row.get("product_name") or "-").strip()
            p = safe_float(row.get("price"))
            preview_lines.append(f"- {m or '-'} / {n} / ￥{format_money(p)}")
    except Exception as query_err:
        logger.warning("产品查询预览失败：%s", query_err, exc_info=True)

    query_desc_bits = []
    if unit_name:
        query_desc_bits.append(f"单位：{unit_name}")
    if model_number:
        query_desc_bits.append(f"型号：{model_number}")
    if keyword and keyword != model_number:
        query_desc_bits.append(f"关键词：{keyword}")
    query_desc = "，".join(query_desc_bits) if query_desc_bits else "按当前输入"
    preview_suffix = (
        f"\n预览命中 {preview_count} 条：\n" + "\n".join(preview_lines)
        if preview_lines else
        ""
    )

    return {
        "success": True,
        "message": "已在副窗打开产品查询",
        "response": (
            f"已帮你打开产品副窗并带入「{keyword or model_number or query_desc}」。"
            "你可以直接在卡片里查看和修改。"
            f"{preview_suffix}"
        ),
        "autoAction": {
            "type": "show_products_float",
            "feature": "products",
            "query": keyword or model_number,
        },
        "data": {
            "routing": "normal_slot_dispatch",
            "intent": "product_query",
            "slots": route_slots,
        },
    }


def run_workflow_products_query_normal_profile(
    user_message: str,
    node_params: Optional[Dict[str, Any]] = None,
    per_page: int = 20,
) -> Dict[str, Any]:
    """工作流 products.query 在普通工具画像下：与普通版 product_query 相同 keyword 策略。"""
    node_params = dict(node_params or {})
    text = (user_message or "").strip()
    rr = route_normal_mode_message(text)
    kw_preview = ""
    if rr.get("intent") == "product_query":
        route_slots = rr.get("slots") or {}
        keyword = str(route_slots.get("keyword") or "").strip()
        model_number = str(route_slots.get("model_number") or "").strip().upper()
        kw_preview = (keyword or "").strip() or (model_number or "").strip()
    if not kw_preview:
        kw_preview = (
            str(node_params.get("keyword") or "").strip()
            or str(node_params.get("model_number") or "").strip().upper()
            or str(node_params.get("product_name") or node_params.get("name") or "").strip()
            or text
        )
    try:
        from app.bootstrap import get_products_service

        svc = get_products_service()
        result = svc.get_products(
            unit_name=None,
            model_number=None,
            keyword=kw_preview or None,
            page=1,
            per_page=per_page,
        ) or {}
        return {
            "success": bool(result.get("success")),
            "data": result.get("data", []),
            "raw": result,
            "normal_tool_profile": True,
        }
    except Exception as err:
        logger.warning("normal_profile products.query 失败：%s", err, exc_info=True)
        return {"success": False, "message": str(err), "data": [], "normal_tool_profile": True}


def resolve_tool_execution_profile(runtime_context: Optional[Dict[str, Any]]) -> str:
    """返回 normal | pro_default。"""
    rc = dict(runtime_context or {})
    explicit = str(rc.get("tool_execution_profile") or "").strip().lower()
    if explicit == "normal":
        return "normal"
    if explicit in ("pro_default", "pro", "professional"):
        return "pro_default"
    us = str(rc.get("ui_surface") or "").strip().lower()
    ic = str(rc.get("intent_channel") or "pro").strip().lower()
    if us == "normal" and ic == "pro":
        return "normal"
    return "pro_default"


def run_normal_slot_shipment_preview(order_text: str) -> Dict[str, Any]:
    """
    normal_slot_dispatch.shipment_preview：与普通版 unified_chat shipment 分支同源（编号解析 + 预览任务）。
    延迟导入避免循环依赖。
    """
    text = (order_text or "").strip()
    if not text:
        return {"success": False, "message": "缺少 order_text", "data": {}}

    from app.routes.tools import _parse_order_text

    parsed = _parse_order_text(text)
    if not parsed.get("success"):
        return {
            "success": True,
            "message": "处理完成",
            "response": str(parsed.get("message") or "订单信息不完整，请补充单位/桶数/型号/规格。"),
            "data": {"text": parsed.get("message"), "action": "followup", "data": {"parsed_data": parsed}},
            "normal_slot_dispatch": True,
        }

    from app.routes import ai_chat as ai_chat_mod

    body = ai_chat_mod.build_shipment_preview_response_dict(
        parsed.get("unit_name", ""),
        parsed.get("products") or [],
        text,
    )
    body["normal_slot_dispatch"] = True
    return body


def run_normal_slot_product_query_from_message(message: str) -> Dict[str, Any]:
    """normal_slot_dispatch.product_query：整段响应 dict（含 autoAction）。"""
    rr = route_normal_mode_message(message or "")
    body = build_product_query_response_dict(rr)
    if body is None:
        return {
            "success": False,
            "message": "当前话术未识别为普通版产品查询槽位",
            "data": {"intent": rr.get("intent"), "slots": rr.get("slots")},
        }
    body["normal_slot_dispatch"] = True
    return body
