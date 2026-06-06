"""
与归档 ``ai_chat`` 路由共用的纯 Python 辅助函数。

供 ``normal_chat_dispatch``、``/api/ai/chat-unified`` 等原生 FastAPI 路由复用。
"""

from __future__ import annotations

import logging
from typing import Any

from app.utils.ai_helpers import format_money, safe_float

logger = logging.getLogger(__name__)


def _fetch_product_meta_by_models(models, unit_name: str = "") -> dict[str, dict[str, Any]]:
    model_list = [m for m in models if m]
    if not model_list:
        return {}

    meta: dict[str, dict[str, Any]] = {}
    try:
        from app.bootstrap import get_products_service

        products_service = get_products_service()

        def _normalize_model_token(v: Any) -> str:
            text = str(v or "").strip().upper()
            return text.replace(" ", "").replace("-", "")

        def _pick_best_record(records: list, model: str) -> dict[str, Any]:
            if not records:
                return {}
            target = _normalize_model_token(model)
            if not target:
                return records[0] or {}

            for r in records:
                rec_model = _normalize_model_token((r or {}).get("model_number"))
                if rec_model and rec_model == target:
                    return r

            for r in records:
                rec_name = _normalize_model_token((r or {}).get("name"))
                if rec_name and target in rec_name:
                    return r

            for r in records:
                rec_model = _normalize_model_token((r or {}).get("model_number"))
                if rec_model and target in rec_model:
                    return r

            return records[0] or {}

        for model in model_list:
            model_raw = str(model or "").strip()
            model_norm = _normalize_model_token(model_raw)
            records = []

            if unit_name:
                result = (
                    products_service.get_products(model_number=model_raw, unit_name=unit_name) or {}
                )
                records = result.get("data") or []

            if not records:
                result = products_service.get_products(model_number=model_raw) or {}
                records = result.get("data") or []

            if not records:
                result = products_service.get_products(keyword=model_raw) or {}
                records = result.get("data") or []

            if records:
                first = _pick_best_record(records, model_raw)
                meta_payload = {
                    "name": first.get("name") or first.get("product_name") or "",
                    "price": safe_float(first.get("price")),
                }
                if model_raw:
                    meta[model_raw] = meta_payload
                if model_norm:
                    meta[model_norm] = meta_payload
    except Exception as err:
        logger.warning("补全预览产品信息失败：%s", err, exc_info=True)
    return meta


def _build_number_preview_items(unit_name: str, products) -> dict[str, Any]:
    products = products or []
    models = []
    for p in products:
        model = (p.get("model_number") or p.get("model") or "").strip()
        if model:
            models.append(model)
    product_meta = _fetch_product_meta_by_models(models, unit_name)

    items = []
    grand_total = 0.0
    has_priced_row = False

    for p in products:
        model = (p.get("model_number") or p.get("model") or p.get("name") or "").strip()
        qty_num = safe_float(p.get("quantity_tins"))
        qty = int(qty_num) if qty_num is not None and qty_num.is_integer() else (qty_num or 0)
        spec = p.get("tin_spec") or p.get("spec") or ""
        spec_num = safe_float(spec)

        model_norm = str(model).strip().upper().replace(" ", "").replace("-", "") if model else ""
        meta = {}
        if model:
            meta = product_meta.get(model, {}) or product_meta.get(model_norm, {}) or {}

        product_name_raw = str(p.get("name") or p.get("product_name") or "").strip()
        if product_name_raw in {"-", "--", "—", "－"}:
            product_name_raw = ""
        product_name = product_name_raw or meta.get("name") or "-"

        unit_price = safe_float(p.get("unit_price"))
        if unit_price is None:
            unit_price = safe_float(p.get("price"))
        if unit_price is None:
            unit_price = safe_float(meta.get("price"))

        line_total = None
        parsed_amount = safe_float(p.get("amount"))
        if unit_price is not None:
            quantity_kg = safe_float(p.get("quantity_kg"))
            if quantity_kg is None and qty_num is not None and spec_num is not None:
                quantity_kg = float(qty_num) * float(spec_num)
            if quantity_kg is not None:
                line_total = unit_price * quantity_kg
            elif qty_num is not None:
                line_total = unit_price * float(qty_num)
        if line_total is None:
            line_total = parsed_amount
        if line_total is not None:
            grand_total += line_total
            has_priced_row = True

        items.append(
            {
                "单位": unit_name or "",
                "型号": model,
                "产品名称": product_name,
                "桶数": qty,
                "规格": spec,
                "单价": format_money(unit_price),
                "总价": format_money(line_total),
            }
        )

    return {
        "items": items,
        "grand_total": grand_total if has_priced_row else None,
    }


def build_shipment_preview_response_dict(
    unit_name: str, products, order_text: str
) -> dict[str, Any]:
    preview = _build_number_preview_items(unit_name, products)
    total_text = (
        f"，预估总价 ¥{format_money(preview['grand_total'])}"
        if preview.get("grand_total") is not None
        else ""
    )
    items = preview["items"]
    return {
        "success": True,
        "message": "已识别订单，请确认执行",
        "response": '已识别订单，请点击"确认执行"生成发货单。',
        "task": {
            "type": "shipment_generate",
            "title": "发货单预览",
            "description": f"单位：{unit_name}，共 {len(products or [])} 项{total_text}。确认后将生成并可继续打印。",
            "items": items,
            "api_url": "/api/tools/execute",
            "method": "POST",
            "payload": {
                "tool_id": "shipment_generate",
                "action": "执行",
                "params": {
                    "order_text": order_text,
                    "unit_name": unit_name,
                    "products": products or [],
                    "number_mode": True,
                },
            },
            "switch_view": "orders",
        },
        "data": {
            "routing": "normal_slot_dispatch",
            "intent": "shipment_preview",
        },
    }


def recognize_intents(message: str) -> dict[str, Any]:
    from app.application.intent_recognition_app import recognize_intents as _recognize
    from app.domain.neuro import ReflexType, get_reflex_arc

    result = _recognize(message)
    return {
        "primary_intent": result.get("primary_intent"),
        "tool_key": result.get("tool_key"),
        "intent_hints": result.get("intent_hints", []),
        "is_negated": result.get("is_negated", False),
        "is_greeting": result.get("is_greeting", False),
        "is_goodbye": result.get("is_goodbye", False),
        "is_help": result.get("is_help", False),
        "confidence": result.get("confidence", 0.5),
        "sources_used": result.get("sources_used", ["rule_engine"]),
    }


def _resolve_mode_scoped_user_id(
    requested_user_id: Any,
    remote_addr: str,
    mode_channel: str,
) -> str:
    raw = str(requested_user_id or "").strip()
    if raw:
        return raw
    ip = str(remote_addr or "unknown")
    channel = str(mode_channel or "default").strip().lower() or "default"
    return f"user_{ip}:{channel}"


def normalize_batch_messages_payload(data: dict[str, Any]) -> list:
    raw = data.get("messages") or data.get("message_list") or []
    if isinstance(raw, str):
        raw = [raw]
    out = []
    for m in raw:
        s = str(m).strip()
        if s:
            out.append(s)
    return out


def unified_chat_single_payload(
    message: str,
    requested_user_id: str,
    remote_addr: str,
    source: str,
    mode: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from app.utils.ai_helpers import is_pro_source, is_professional_mode, is_qclaw_source

    if (is_pro_source(source) or is_professional_mode(mode)) and not is_qclaw_source(source):
        return {
            "success": False,
            "message": "专业版请求禁止使用 /api/ai/unified_chat，请改用 /api/ai/chat",
            "mode_guard": "normal_only",
            "_http_status": 400,
        }

    text = str(message or "").strip()
    excel_analysis = (context or {}).get("excel_analysis") if isinstance(context, dict) else None
    if isinstance(excel_analysis, dict) and any(
        k in text for k in ("数据库", "入库", "导入", "添加到库", "加入")
    ):
        from app.application import get_ai_chat_app_service

        ai_chat_service = get_ai_chat_app_service()
        result = ai_chat_service.process_chat(
            user_id=_resolve_mode_scoped_user_id(requested_user_id, remote_addr, "normal"),
            message=message,
            context=context,
            source="normal",
            file_context={},
        )
        return result

    from app.application.normal_chat_dispatch import (
        build_product_query_response_dict,
        route_normal_mode_message,
    )

    route_result = route_normal_mode_message(message)
    route_intent = route_result.get("intent")

    if route_intent == "shipment":
        try:
            from app.routes.tools import _parse_order_text

            parsed_retry = _parse_order_text(message)
            if parsed_retry.get("success"):
                body = build_shipment_preview_response_dict(
                    parsed_retry.get("unit_name", ""),
                    parsed_retry.get("products") or [],
                    message,
                )
                return body

            local_msg = parsed_retry.get("message", "订单信息不完整，请补充单位/桶数/型号/规格。")
            return {
                "success": True,
                "message": "处理完成",
                "response": local_msg,
                "data": {
                    "text": local_msg,
                    "action": "followup",
                    "data": {"parsed_data": parsed_retry},
                },
            }
        except Exception as local_parse_err:
            logger.error("普通版本地编号解析异常：%s", local_parse_err, exc_info=True)
            return {
                "success": False,
                "message": f"编号模式处理失败：{str(local_parse_err)}",
                "_http_status": 500,
            }

    if route_intent == "product_query":
        body = build_product_query_response_dict(route_result)
        if body:
            return body

    return {
        "success": True,
        "message": "处理完成",
        "response": (
            "普通版里这是两套独立能力，请分开描述："
            "① 发货单/开单：用编号或口语描述订单（说法里常带「发货单、开单、打印」等）。"
            "② 产品库查询：查型号、价格（例如「查询七彩乐园的9803」），不会生成发货单。"
        ),
        "data": {
            "text": "普通版：发货单开单 与 产品库查询 为两套独立能力，请分开描述。",
            "action": "followup",
            "data": {"mode": "normal_slot_dispatch"},
        },
    }
