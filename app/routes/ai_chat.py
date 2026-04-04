# -*- coding: utf-8 -*-
"""
AI 聊天路由模块

提供 AI 聊天接口，包括：
- /api/ai/chat: 统一聊天接口
- /api/ai/chat-unified: 兼容旧版
- /api/ai/chat/stream: 流式响应
- /api/ai/file/analyze: 文件分析
- /api/ai/sqlite/import_unit_products: 产品导入
"""

import asyncio
import json
import logging
import os
import uuid
import urllib.error
import urllib.request
from io import BytesIO
from typing import Any, Dict, Optional

from flasgger import swag_from
from flask import Blueprint, current_app, jsonify, request, send_file

from app.utils.path_utils import get_upload_dir
from app.utils.rate_limiter import check_rate_limit
from app.utils.ai_helpers import (
    is_pro_source,
    is_qclaw_source,
    is_professional_mode,
    safe_float,
    format_money,
)
from app.application.normal_chat_dispatch import (
    route_normal_mode_message,
    build_product_query_response_dict,
)

logger = logging.getLogger(__name__)

ai_chat_bp = Blueprint("ai_chat", __name__, url_prefix="/api/ai")

_QCLOW_RUNTIME_STATE: Dict[str, Any] = {
    "wechat_open": True,
    "openclaw_base": "http://localhost:28789",
    "whitelist": {
        "/api/ai/chat": True,
        "/api/ai/unified_chat": True,
        "/api/wechat_contacts": True,
        "/api/shipment/orders": True,
        "/api/print/printers": True,
    },
}


def _resolve_mode_scoped_user_id(
    requested_user_id: Any,
    remote_addr: str,
    mode_channel: str,
) -> str:
    """
    构造模式隔离的 user_id，防止专业/普通共享同一会话上下文而串流。

    规则：
    - 显式传入 user_id 时原样使用（兼容已有调用方）。
    - 未传时按 channel 自动加后缀，如 user_127.0.0.1:pro / :normal。
    """
    raw = str(requested_user_id or "").strip()
    if raw:
        return raw
    ip = str(remote_addr or "unknown")
    channel = str(mode_channel or "default").strip().lower() or "default"
    return f"user_{ip}:{channel}"


def build_shipment_preview_response_dict(unit_name: str, products, order_text: str) -> Dict[str, Any]:
    """发货单预览响应体（dict），与 _build_number_preview_response 内容一致，供工具层与非 Flask 调用方复用。"""
    preview = _build_number_preview_items(unit_name, products)
    total_text = f"，预估总价 ¥{format_money(preview['grand_total'])}" if preview.get("grand_total") is not None else ""
    items = preview["items"]
    return {
        "success": True,
        "message": "已识别订单，请确认执行",
        "response": "已识别订单，请点击\"确认执行\"生成发货单。",
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


def _fetch_product_meta_by_models(models, unit_name: str = "") -> Dict[str, Dict[str, Any]]:
    """
    按型号批量补全产品名称/单价（用于发货单预览展示）。
    """
    model_list = [m for m in models if m]
    if not model_list:
        return {}

    meta: Dict[str, Dict[str, Any]] = {}
    try:
        from app.bootstrap import get_products_service

        products_service = get_products_service()
        def _normalize_model_token(v: Any) -> str:
            text = str(v or "").strip().upper()
            return text.replace(" ", "").replace("-", "")

        def _pick_best_record(records: list, model: str) -> Dict[str, Any]:
            if not records:
                return {}
            target = _normalize_model_token(model)
            if not target:
                return records[0] or {}

            # 1) 精确命中 model_number
            for r in records:
                rec_model = _normalize_model_token((r or {}).get("model_number"))
                if rec_model and rec_model == target:
                    return r

            # 2) 名称中包含型号 token
            for r in records:
                rec_name = _normalize_model_token((r or {}).get("name"))
                if rec_name and target in rec_name:
                    return r

            # 3) model_number 模糊包含
            for r in records:
                rec_model = _normalize_model_token((r or {}).get("model_number"))
                if rec_model and target in rec_model:
                    return r

            return records[0] or {}

        for model in model_list:
            model_raw = str(model or "").strip()
            model_norm = _normalize_model_token(model_raw)
            records = []

            # 1) 优先按「单位 + 型号」查（如果有单位）
            if unit_name:
                result = products_service.get_products(model_number=model_raw, unit_name=unit_name) or {}
                records = result.get("data") or []

            # 2) 兜底按「型号」全局查，避免单位过滤过严导致查不到
            if not records:
                result = products_service.get_products(model_number=model_raw) or {}
                records = result.get("data") or []

            # 3) 最后兜底按关键词查（部分数据可能未严格维护 model_number 字段）
            if not records:
                result = products_service.get_products(keyword=model_raw) or {}
                records = result.get("data") or []

            if records:
                first = _pick_best_record(records, model_raw)
                meta_payload = {
                    "name": first.get("name") or first.get("product_name") or "",
                    "price": safe_float(first.get("price")),
                }
                # 同时按“原始型号”和“归一化型号”建索引，避免 key 形态不一致导致补全丢失。
                if model_raw:
                    meta[model_raw] = meta_payload
                if model_norm:
                    meta[model_norm] = meta_payload
    except Exception as err:
        logger.warning("补全预览产品信息失败：%s", err, exc_info=True)
    return meta

def _build_number_preview_items(unit_name: str, products) -> Dict[str, Any]:
    """
    生成发货单预览表格项，包含：产品名称、单价、总价。
    """
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

        # 总价口径：
        # 优先按数量推导（数量KG > 桶数*规格 > 桶数），仅在无法推导时回退 parsed amount。
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

        items.append({
            "单位": unit_name or "",
            "型号": model,
            "产品名称": product_name,
            "桶数": qty,
            "规格": spec,
            "单价": format_money(unit_price),
            "总价": format_money(line_total),
        })

    return {
        "items": items,
        "grand_total": grand_total if has_priced_row else None,
    }

def _build_number_preview_response(unit_name: str, products, order_text: str):
    """生成发货单预览响应（统一函数，供chat和chat_unified共用）"""
    return jsonify(build_shipment_preview_response_dict(unit_name, products, order_text))

def get_ai_service():
    """获取 AI 对话服务实例"""
    from app.services import get_ai_conversation_service
    return get_ai_conversation_service()

def set_file_pending_confirmation(user_id: str, pending_data: Dict[str, Any]) -> None:
    """设置文件上传待确认上下文"""
    ai_service = get_ai_service()
    ai_service.set_pending_confirmation(user_id, pending_data)

def recognize_intents(message: str) -> Dict[str, Any]:
    """导入意图识别函数 (使用新的领域服务)"""
    from app.domain.services.intent_recognition_service import get_intent_recognition_service
    service = get_intent_recognition_service()
    result = service.recognize(message)
    # 保持与旧接口兼容的字典返回格式
    return {
        "primary_intent": result.primary_intent,
        "tool_key": result.tool_key,
        "intent_hints": result.intent_hints,
        "is_negated": result.is_negated,
        "is_greeting": result.is_greeting,
        "is_goodbye": result.is_goodbye,
        "is_help": result.is_help,
        "confidence": result.confidence,
        "sources_used": result.sources_used,
    }

@ai_chat_bp.route("/chat", methods=["POST"])
@swag_from({
    'summary': 'AI 聊天',
    'description': '统一 AI 聊天接口，支持意图识别和工具调用',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': '用户消息'},
                    'user_id': {'type': 'string', 'description': '用户 ID（可选）'},
                    'context': {'type': 'object', 'description': '额外上下文（可选）'}
                },
                'required': ['message']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'}
                }
            }
        }
    }
})
def chat():
    """
    AI 聊天接口

    请求格式：
    {
        "message": "用户消息",
        "user_id": "用户 ID（可选，默认使用 session）",
        "context": {}  # 额外上下文（可选）
    }

    响应格式：
    {
        "success": True/False,
        "message": "响应消息",
        "data": {
            "text": "AI 回复文本",
            "action": "动作类型",
            "data": {}  # 额外数据
        }
    }
    """
    try:
        data = request.json if request.is_json else {}
        message = data.get("message", "")
        requested_user_id = data.get("user_id")
        context = data.get("context", {})
        source = (data.get("source") or "").strip().lower()
        mode = data.get("mode")
        file_context = data.get("file_context", {})
        excel_index_id = str(data.get("excel_index_id") or "").strip()
        excel_top_k = data.get("excel_top_k")

        if excel_index_id:
            if not isinstance(context, dict):
                context = {}
            context["excel_index_id"] = excel_index_id
            if excel_top_k is not None:
                context["excel_top_k"] = excel_top_k

        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400

        # /chat 默认仅专业版；Qclaw 生态可通行专业链路。
        if not (is_pro_source(source) or is_professional_mode(mode) or is_qclaw_source(source)):
            return jsonify({
                "success": False,
                "message": "普通版请求禁止使用 /api/ai/chat，请改用 /api/ai/unified_chat",
                "mode_guard": "professional_only",
            }), 400
        source = "qclaw" if is_qclaw_source(source) else "pro"
        user_channel = "qclaw-pro" if source == "qclaw" else "pro"
        user_id = _resolve_mode_scoped_user_id(requested_user_id, request.remote_addr, user_channel)

        rate_limit_result = check_rate_limit(
            user_id=user_id,
            endpoint="ai_chat",
            max_requests=10,
            window_seconds=60
        )
        if not rate_limit_result.get("allowed"):
            return jsonify({
                "success": False,
                "message": "请求过于频繁，请稍后再试",
                "retry_after": rate_limit_result.get("retry_after", 60)
            }), 429

        from app.application import get_ai_chat_app_service
        ai_chat_service = get_ai_chat_app_service()

        result = ai_chat_service.process_chat(
            user_id=user_id,
            message=message,
            context=context,
            source=source,
            file_context=file_context
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"聊天接口异常：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"处理失败：{str(e)}",
        }), 500


def _normalize_batch_messages_payload(data: Dict[str, Any]) -> list:
    """从 JSON 中解析 messages / message_list，去空、去首尾空白。"""
    raw = data.get("messages") or data.get("message_list") or []
    if isinstance(raw, str):
        raw = [raw]
    out = []
    for m in raw:
        s = str(m).strip()
        if s:
            out.append(s)
    return out


def _unified_chat_single_payload(
    message: str,
    requested_user_id: str,
    remote_addr: str,
    source: str,
    mode: Any,
) -> Dict[str, Any]:
    """
    与 chat_unified 单条逻辑一致，返回可 JSON 序列化的 dict。
    若需非 200 HTTP 状态，附带键 _http_status。
    """
    # /unified_chat 默认仅普通版；Qclaw 生态允许同时调用普通/专业链路。
    if (is_pro_source(source) or is_professional_mode(mode)) and not is_qclaw_source(source):
        return {
            "success": False,
            "message": "专业版请求禁止使用 /api/ai/unified_chat，请改用 /api/ai/chat",
            "mode_guard": "normal_only",
            "_http_status": 400,
        }

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
                "data": {"text": local_msg, "action": "followup", "data": {"parsed_data": parsed_retry}},
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


@ai_chat_bp.route("/chat/batch", methods=["POST"])
def chat_batch():
    """
    专业链路批量：按顺序对每条消息调用 process_chat（共享会话 user_id）。
    用于前端合并短时间内的多次发送，减少 HTTP 往返。
    """
    try:
        data = request.json if request.is_json else {}
        messages = _normalize_batch_messages_payload(data)
        if not messages:
            return jsonify({"success": False, "message": "messages 不能为空"}), 400
        if len(messages) > 20:
            return jsonify({"success": False, "message": "单次批量最多 20 条"}), 400

        requested_user_id = data.get("user_id")
        context = data.get("context", {})
        source = (data.get("source") or "").strip().lower()
        mode = data.get("mode")
        file_context = data.get("file_context", {})
        excel_index_id = str(data.get("excel_index_id") or "").strip()
        excel_top_k = data.get("excel_top_k")

        if excel_index_id:
            if not isinstance(context, dict):
                context = {}
            context["excel_index_id"] = excel_index_id
            if excel_top_k is not None:
                context["excel_top_k"] = excel_top_k

        if not (is_pro_source(source) or is_professional_mode(mode) or is_qclaw_source(source)):
            return jsonify({
                "success": False,
                "message": "普通版请求禁止使用 /api/ai/chat/batch，请改用 /api/ai/unified_chat/batch",
                "mode_guard": "professional_only",
            }), 400

        source = "qclaw" if is_qclaw_source(source) else "pro"
        user_channel = "qclaw-pro" if source == "qclaw" else "pro"
        user_id = _resolve_mode_scoped_user_id(requested_user_id, request.remote_addr, user_channel)

        rate_limit_result = check_rate_limit(
            user_id=user_id,
            endpoint="ai_chat_batch",
            max_requests=5,
            window_seconds=60,
        )
        if not rate_limit_result.get("allowed"):
            return jsonify({
                "success": False,
                "message": "请求过于频繁，请稍后再试",
                "retry_after": rate_limit_result.get("retry_after", 60),
            }), 429

        from app.application import get_ai_chat_app_service

        ai_chat_service = get_ai_chat_app_service()
        results: list = []
        for msg in messages:
            one = ai_chat_service.process_chat(
                user_id=user_id,
                message=msg,
                context=context,
                source=source,
                file_context=file_context,
            )
            results.append(one)

        all_ok = all(bool(r.get("success")) for r in results if isinstance(r, dict))
        return jsonify({
            "success": all_ok,
            "results": results,
            "count": len(results),
            "batch": True,
        })
    except Exception as e:
        logger.error(f"批量聊天接口异常：{e}", exc_info=True)
        return jsonify({"success": False, "message": f"处理失败：{str(e)}"}), 500


@ai_chat_bp.route("/unified_chat/batch", methods=["POST"])
@ai_chat_bp.route("/chat-unified/batch", methods=["POST"])
def unified_chat_batch():
    """普通版统一聊天批量：顺序执行每条消息的槽位路由逻辑。"""
    try:
        data = request.json if request.is_json else {}
        messages = _normalize_batch_messages_payload(data)
        if not messages:
            return jsonify({"success": False, "message": "messages 不能为空"}), 400
        if len(messages) > 20:
            return jsonify({"success": False, "message": "单次批量最多 20 条"}), 400

        requested_user_id = data.get("user_id")
        source = (data.get("source") or "").strip().lower()
        mode = data.get("mode")

        if (is_pro_source(source) or is_professional_mode(mode)) and not is_qclaw_source(source):
            return jsonify({
                "success": False,
                "message": "专业版请求禁止使用 /api/ai/unified_chat/batch，请改用 /api/ai/chat/batch",
                "mode_guard": "normal_only",
            }), 400

        results: list = []
        for msg in messages:
            payload = _unified_chat_single_payload(msg, requested_user_id, request.remote_addr, source, mode)
            status = int(payload.pop("_http_status", 200))
            if status >= 400:
                payload["_http_status"] = status
            results.append(payload)

        all_ok = all(bool(r.get("success")) for r in results if isinstance(r, dict))
        return jsonify({
            "success": all_ok,
            "results": results,
            "count": len(results),
            "batch": True,
        })
    except Exception as e:
        logger.error(f"统一批量聊天接口异常：{e}", exc_info=True)
        return jsonify({"success": False, "message": f"处理失败：{str(e)}"}), 500


@ai_chat_bp.route("/chat-unified", methods=["POST"])
@ai_chat_bp.route("/unified_chat", methods=["POST"])
def chat_unified():
    """
    普通版统一聊天接口（逻辑匹配优先）。

    设计目标：
    - 普通版与专业版彻底双线：普通版不回退到专业版意图链路。
    - 普通版仅处理传统发货单编号模式（number_mode=True）。
    """
    try:
        data = request.json if request.is_json else {}
        message = (data.get("message", "") or "").strip()
        requested_user_id = data.get("user_id")
        source = (data.get("source") or "").strip().lower()
        mode = data.get("mode")

        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400

        payload = _unified_chat_single_payload(message, requested_user_id, request.remote_addr, source, mode)
        status = int(payload.pop("_http_status", 200))
        return jsonify(payload), status
    except Exception as e:
        logger.error(f"统一聊天接口异常：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"处理失败：{str(e)}",
        }), 500

@ai_chat_bp.route("/qclaw/routes", methods=["GET"])
def qclaw_routes():
    """Qclaw 生态可调用路由清单（普通+专业）。"""
    return jsonify({
        "success": True,
        "source": "qclaw",
        "permissions": {
            "normal_routes": [
                "/api/ai/unified_chat",
                "/api/tools/execute",
                "/api/products/*",
                "/api/customers/*",
                "/api/materials/*",
            ],
            "pro_routes": [
                "/api/ai/chat",
                "/api/ai/chat/stream",
                "/api/wechat/*",
                "/api/wechat_contacts/*",
                "/api/shipment/*",
                "/api/print/*",
            ],
        },
        "note": "Qclaw 来源允许同时访问普通版与专业版主链路。",
    })

@ai_chat_bp.route("/qclaw/panel", methods=["GET"])
def qclaw_panel():
    """获取 Qclaw 路由调度面板状态。"""
    whitelist = _QCLOW_RUNTIME_STATE.get("whitelist", {})
    routes = [
        {"path": path, "enabled": bool(enabled)}
        for path, enabled in whitelist.items()
    ]
    return jsonify({
        "success": True,
        "wechat_open": bool(_QCLOW_RUNTIME_STATE.get("wechat_open", False)),
        "openclaw_base": str(_QCLOW_RUNTIME_STATE.get("openclaw_base", "http://127.0.0.1:28789")),
        "routes": routes,
    })

@ai_chat_bp.route("/qclaw/wechat-gateway", methods=["POST"])
def qclaw_wechat_gateway():
    """设置 Qclaw 微信开放权限开关。"""
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled", False))
    _QCLOW_RUNTIME_STATE["wechat_open"] = enabled
    return jsonify({
        "success": True,
        "wechat_open": enabled,
    })

@ai_chat_bp.route("/qclaw/openclaw/config", methods=["POST"])
def qclaw_openclaw_config():
    """设置 OpenClaw 网关地址。"""
    data = request.get_json(silent=True) or {}
    base_url = str(data.get("base_url") or "").strip().rstrip("/")
    if not base_url:
        return jsonify({"success": False, "message": "base_url 不能为空"}), 400
    _QCLOW_RUNTIME_STATE["openclaw_base"] = base_url
    return jsonify({"success": True, "openclaw_base": base_url})

@ai_chat_bp.route("/qclaw/whitelist", methods=["POST"])
def qclaw_whitelist_update():
    """更新 Qclaw 路由白名单项。"""
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    enabled = bool(data.get("enabled", False))
    if not path:
        return jsonify({"success": False, "message": "path 不能为空"}), 400
    whitelist = _QCLOW_RUNTIME_STATE.setdefault("whitelist", {})
    whitelist[path] = enabled
    return jsonify({"success": True, "path": path, "enabled": enabled})

@ai_chat_bp.route("/qclaw/test-route", methods=["POST"])
def qclaw_test_route():
    """一键测试单条路由（内部 test_client 调用）。"""
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    method = str(data.get("method") or "GET").upper()
    if not path:
        return jsonify({"success": False, "message": "path 不能为空"}), 400
    whitelist = _QCLOW_RUNTIME_STATE.get("whitelist", {})
    if not bool(whitelist.get(path, False)):
        return jsonify({"success": False, "message": "该路由未在白名单启用"}), 403

    try:
        with current_app.test_client() as client:
            if method == "POST":
                resp = client.post(path, json={"source": "qclaw", "message": "smoke"})
            else:
                resp = client.get(path)
            ok = resp.status_code < 500
            return jsonify({
                "success": True,
                "path": path,
                "method": method,
                "status_code": resp.status_code,
                "result": "ok" if ok else "error",
            })
    except Exception as err:
        return jsonify({
            "success": False,
            "path": path,
            "method": method,
            "message": str(err),
        }), 500

@ai_chat_bp.route("/qclaw/openclaw/chat", methods=["POST"])
def qclaw_openclaw_chat():
    """转发到 OpenClaw 本地 REST API。"""
    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "message": "message 不能为空"}), 400

    base = str(_QCLOW_RUNTIME_STATE.get("openclaw_base", "http://localhost:28789")).rstrip("/")
    target_url = f"{base}/api/chat"
    payload = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        target_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {"raw": raw}
            return jsonify({
                "success": True,
                "target": target_url,
                "data": parsed,
            })
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        return jsonify({
            "success": False,
            "target": target_url,
            "status_code": err.code,
            "message": body or str(err),
        }), 502
    except Exception as err:
        return jsonify({
            "success": False,
            "target": target_url,
            "message": str(err),
        }), 502

@ai_chat_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """AI 聊天流式接口（Server-Sent Events）"""
    try:
        import json

        from flask import Response

        data = request.json if request.is_json else {}
        message = data.get("message", "")
        user_id = data.get("user_id", f"user_{request.remote_addr}")

        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400

        def generate():
            ai_service = get_ai_service()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    ai_service.chat(user_id, message, {})
                )
                yield f"data: {json.dumps(result)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                loop.close()

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"流式聊天接口异常：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"流式处理失败：{str(e)}",
        }), 500

@ai_chat_bp.route("/context", methods=["GET"])
def get_context():
    """获取对话上下文"""
    try:
        user_id = request.args.get("user_id", f"user_{id(request.remote_addr)}")

        ai_service = get_ai_service()
        context = ai_service.get_context(user_id)

        if not context:
            return jsonify({
                "success": True,
                "message": "未找到对话上下文",
                "data": None,
            })

        return jsonify({
            "success": True,
            "data": {
                "user_id": context.user_id,
                "conversation_history": context.conversation_history,
                "current_file": context.current_file,
                "last_action": context.last_action,
                "metadata": context.metadata,
            },
        })

    except Exception as e:
        logger.error(f"获取上下文失败：{e}")
        return jsonify({
            "success": False,
            "message": f"获取上下文失败：{str(e)}",
        }), 500

@ai_chat_bp.route("/context/clear", methods=["POST"])
def clear_context():
    """清除对话上下文"""
    try:
        data = request.json if request.is_json else {}
        user_id = data.get("user_id", f"user_{id(request.remote_addr)}")

        ai_service = get_ai_service()
        success = ai_service.clear_context(user_id)

        return jsonify({
            "success": success,
            "message": "上下文已清除" if success else "未找到上下文",
        })

    except Exception as e:
        logger.error(f"清除上下文失败：{e}")
        return jsonify({
            "success": False,
            "message": f"清除上下文失败：{str(e)}",
        }), 500

@ai_chat_bp.route("/config", methods=["GET"])
def get_config():
    """获取 AI 配置"""
    try:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")

        return jsonify({
            "success": True,
            "data": {
                "api_configured": bool(api_key),
                "model": "deepseek-chat",
                "features": [
                    "意图识别",
                    "工具调用",
                    "AI 对话",
                    "上下文管理",
                    "流式输出",
                ],
            },
        })

    except Exception as e:
        logger.error(f"获取配置失败：{e}")
        return jsonify({
            "success": False,
            "message": f"获取配置失败：{str(e)}",
        }), 500

@ai_chat_bp.route("/test", methods=["GET"])
def test():
    """测试 AI 服务"""
    return jsonify({
        "success": True,
        "message": "AI 聊天服务运行正常",
        "timestamp": __import__("time").time(),
    })

@ai_chat_bp.route("/intent/test", methods=["POST"])
def test_intent():
    """测试意图识别"""
    try:
        data = request.json if request.is_json else {}
        message = data.get("message", "")

        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400

        intent_result = recognize_intents(message)

        return jsonify({
            "success": True,
            "data": intent_result,
        })

    except Exception as e:
        logger.error(f"意图识别测试失败：{e}")
        return jsonify({
            "success": False,
            "message": f"意图识别失败：{str(e)}",
        }), 500

@ai_chat_bp.route("/kitten/business-snapshot", methods=["GET"])
def kitten_business_snapshot():
    """
    小猫分析：返回业务库（原材料、产品、出货）文本摘要与统计，供前端展示或调试；
    对话场景下由服务端在 kitten_include_business_db 为真时自动注入，无需客户端重复传大段文本。
    """
    try:
        from app.services.kitten_business_snapshot import build_kitten_business_snapshot

        snap = build_kitten_business_snapshot()
        return jsonify({"success": True, "data": snap})
    except Exception as e:
        logger.exception("kitten business-snapshot 失败：%s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@ai_chat_bp.route("/kitten/report/export", methods=["POST"])
def export_kitten_report():
    """
    小猫分析导出（混合模式）：
    - 前端上传会话/摘要
    - 后端执行插件算法并生成 XLSX
    """
    try:
        payload = request.get_json(silent=True) or {}
        from app.services.kitten_report import KittenReportExportService

        service = KittenReportExportService()
        report = service.build_report(payload)
        file_name = str(report.get("file_name") or "小猫分析报告.xlsx")
        content = report.get("content") or b""

        return send_file(
            BytesIO(content),
            as_attachment=True,
            download_name=file_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        logger.exception(f"小猫分析导出失败：{e}")
        return jsonify({
            "success": False,
            "message": f"导出失败：{str(e)}"
        }), 500

@ai_chat_bp.route("/kitten/charts/all", methods=["GET"])
def kitten_get_all_charts():
    """获取所有图表数据"""
    try:
        from app.services.kitten_report.chart_data_service import chart_service

        data = chart_service.get_all_charts_data()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.exception("获取图表数据失败：%s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@ai_chat_bp.route("/kitten/charts/revenue", methods=["GET"])
def kitten_revenue_chart():
    """获取营收趋势图表数据"""
    try:
        from app.services.kitten_report.chart_data_service import chart_service
        months = int(request.args.get("months", 6))
        data = chart_service.get_revenue_chart_data(months)
        return jsonify(data)
    except Exception as e:
        logger.exception("获取营收图表失败：%s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@ai_chat_bp.route("/kitten/charts/products", methods=["GET"])
def kitten_product_chart():
    """获取产品销售占比图表数据"""
    try:
        from app.services.kitten_report.chart_data_service import chart_service
        data = chart_service.get_product_pie_chart_data()
        return jsonify(data)
    except Exception as e:
        logger.exception("获取产品图表失败：%s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@ai_chat_bp.route("/kitten/charts/customers", methods=["GET"])
def kitten_customer_chart():
    """获取客户排行图表数据"""
    try:
        from app.services.kitten_report.chart_data_service import chart_service
        data = chart_service.get_customer_bar_chart_data()
        return jsonify(data)
    except Exception as e:
        logger.exception("获取客户图表失败：%s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@ai_chat_bp.route("/kitten/charts/profit", methods=["GET"])
def kitten_profit_chart():
    """获取利润趋势图表数据"""
    try:
        from app.services.kitten_report.chart_data_service import chart_service
        months = int(request.args.get("months", 6))
        data = chart_service.get_profit_trend_chart_data(months)
        return jsonify(data)
    except Exception as e:
        logger.exception("获取利润图表失败：%s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@ai_chat_bp.route("/kitten/charts/inventory", methods=["GET"])
def kitten_inventory_chart():
    """获取库存分布图表数据"""
    try:
        from app.services.kitten_report.chart_data_service import chart_service
        data = chart_service.get_inventory_chart_data()
        return jsonify(data)
    except Exception as e:
        logger.exception("获取库存图表失败：%s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@ai_chat_bp.route("/kitten/financial/report", methods=["POST"])
def kitten_financial_report():
    """生成财务分析报告并保存"""
    try:
        payload = request.get_json(silent=True) or {}
        metadata = payload.get("metadata") or {}

        from app.services.kitten_report.financial_plugins import FinancialReportPlugin, InventoryValuationPlugin

        fin_plugin = FinancialReportPlugin()
        inv_plugin = InventoryValuationPlugin()

        fin_result = fin_plugin.run(payload)
        inv_result = inv_plugin.run(payload)

        analysis_data = {
            "financial_report": {
                "key": fin_result.key,
                "title": fin_result.title,
                "level": fin_result.level,
                "summary": fin_result.summary,
                "details": fin_result.details,
            },
            "inventory_valuation": {
                "key": inv_result.key,
                "title": inv_result.title,
                "level": inv_result.level,
                "summary": inv_result.summary,
                "details": inv_result.details,
            },
        }

        from app.services.kitten_report.save_service import analysis_save_service

        save_result = analysis_save_service.save_analysis(
            analysis_type="financial",
            data=analysis_data,
            metadata=metadata,
        )

        if save_result.get("success"):
            return jsonify({
                "success": True,
                "analysis_id": save_result.get("id"),
                "data": analysis_data,
                "saved_to": save_result.get("filename"),
                "message": "财务报告已生成并保存",
            })
        else:
            return jsonify({
                "success": True,
                "data": analysis_data,
                "message": "财务报告已生成（保存失败）",
            })
    except Exception as e:
        logger.exception("财务报表生成失败：{e}")
        return jsonify({
            "success": False,
            "message": f"财务报表生成失败：{str(e)}"
        }), 500


@ai_chat_bp.route("/kitten/saved/list", methods=["GET"])
def kitten_saved_list():
    """获取已保存的分析列表"""
    try:
        analysis_type = request.args.get("type")

        from app.services.kitten_report.save_service import analysis_save_service

        analyses = analysis_save_service.list_saved_analyses(analysis_type)
        stats = analysis_save_service.get_statistics_summary()

        return jsonify({
            "success": True,
            "analyses": analyses,
            "statistics": stats,
        })
    except Exception as e:
        logger.exception("获取保存列表失败：%s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@ai_chat_bp.route("/kitten/saved/<analysis_id>", methods=["GET"])
def kitten_get_saved(analysis_id):
    """获取已保存的分析详情"""
    try:
        from app.services.kitten_report.save_service import analysis_save_service

        analysis = analysis_save_service.get_analysis(analysis_id)

        if not analysis:
            return jsonify({"success": False, "message": "未找到该分析记录"}), 404

        return jsonify({"success": True, "data": analysis})
    except Exception as e:
        logger.exception("获取分析详情失败：%s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@ai_chat_bp.route("/kitten/saved/<analysis_id>/export", methods=["GET"])
def kitten_export_saved(analysis_id):
    """导出已保存的分析为 Excel"""
    try:
        from app.services.kitten_report.save_service import analysis_save_service

        result = analysis_save_service.export_analysis_to_xlsx(analysis_id)

        if not result.get("success"):
            return jsonify(result), 400

        file_name = str(result.get("file_name") or "财务报告.xlsx")
        content = result.get("content") or b""

        return send_file(
            BytesIO(content),
            as_attachment=True,
            download_name=file_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        logger.exception("导出失败：%s", e)
        return jsonify({"success": False, "message": f"导出失败：{str(e)}"}), 500


@ai_chat_bp.route("/kitten/saved/<analysis_id>", methods=["DELETE"])
def kitten_delete_saved(analysis_id):
    """删除已保存的分析"""
    try:
        from app.services.kitten_report.save_service import analysis_save_service

        result = analysis_save_service.delete_analysis(analysis_id)

        if result.get("success"):
            return jsonify({"success": True, "message": "删除成功"})
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.exception("删除失败：%s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@ai_chat_bp.route("/file/analyze", methods=["POST"])
def file_analyze():
    """
    统一文件分析接口
    支持 .db（SQLite）读取，返回库内表结构摘要
    """
    try:
        upload_file = request.files.get("file")
        purpose = request.form.get("purpose", "general")

        from app.application import FileAnalysisService, get_file_analysis_app_service
        service = get_file_analysis_app_service()

        result = service.analyze_file(upload_file, purpose)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.exception(f"文件分析失败：{e}")
        return jsonify({
            "success": False,
            "message": f"文件分析失败：{str(e)}"
        }), 500

@ai_chat_bp.route("/sqlite/import_unit_products", methods=["POST"])
def import_unit_products():
    """
    从上传的 SQLite .db 导入购买单位产品
    """
    try:
        payload = request.get_json() or {}
        saved_name = payload.get("saved_name") or ""
        unit_name = (payload.get("unit_name") or payload.get("unit_name_guess") or "").strip()
        create_purchase_unit = bool(payload.get("create_purchase_unit", True))
        skip_duplicates = bool(payload.get("skip_duplicates", True))

        from app.application import UnitProductsImportService, get_unit_products_import_app_service
        service = get_unit_products_import_app_service()

        result = service.import_unit_products(
            saved_name=saved_name,
            unit_name=unit_name,
            create_purchase_unit=create_purchase_unit,
            skip_duplicates=skip_duplicates
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.exception(f"导入购买单位+产品列表失败：{e}")
        return jsonify({
            "success": False,
            "message": f"导入失败：{str(e)}"
        }), 500


@ai_chat_bp.route("/approval/request", methods=["POST"])
def create_approval_request():
    """
    创建审批请求
    """
    try:
        payload = request.get_json() or {}
        plan_id = payload.get("plan_id") or ""
        node_id = payload.get("node_id") or ""
        tool_id = payload.get("tool_id") or ""
        action = payload.get("action") or ""
        params = payload.get("params") or {}

        if not plan_id or not node_id:
            return jsonify({
                "success": False,
                "message": "缺少 plan_id 或 node_id"
            }), 400

        from app.application.workflow import WorkflowNode, get_approval_service
        approval_service = get_approval_service()

        node = WorkflowNode(
            node_id=node_id,
            tool_id=tool_id,
            action=action,
            params=params,
        )

        approval_req = approval_service.create_approval_request(
            plan_id=plan_id,
            node=node,
        )

        return jsonify({
            "success": True,
            "message": "审批请求已创建",
            "data": {
                "request_id": approval_req.request_id,
                "plan_id": approval_req.plan_id,
                "node_id": approval_req.node_id,
                "tool_id": approval_req.tool_id,
                "action": approval_req.action,
                "status": approval_req.status.value,
                "created_at": approval_req.created_at.isoformat() if approval_req.created_at else None,
            }
        }), 200

    except Exception as e:
        logger.exception(f"创建审批请求失败：{e}")
        return jsonify({
            "success": False,
            "message": f"创建审批请求失败：{str(e)}"
        }), 500


@ai_chat_bp.route("/approval/approve", methods=["POST"])
def approve_request():
    """
    审批通过（自审批）
    """
    try:
        payload = request.get_json() or {}
        request_id = payload.get("request_id") or ""
        plan_id = payload.get("plan_id") or ""
        comment = payload.get("comment") or ""

        from app.application.workflow import get_approval_service
        approval_service = get_approval_service()

        actual_request_id = None

        if request_id:
            success = approval_service.approve(request_id, comment)
            actual_request_id = request_id
        elif plan_id:
            pending_req = approval_service.get_pending_request_by_plan(plan_id)
            if not pending_req:
                return jsonify({
                    "success": False,
                    "message": "没有待审批的请求"
                }), 404
            success = approval_service.approve(pending_req.request_id, comment)
            actual_request_id = pending_req.request_id
        else:
            return jsonify({
                "success": False,
                "message": "缺少 request_id 或 plan_id"
            }), 400

        if success:
            workflow_data = approval_service.get_pending_workflow(actual_request_id) if actual_request_id else None
            run_result_data = None

            if workflow_data:
                from app.application.workflow import WorkflowEngine
                plan_obj = workflow_data.get("plan")
                runtime_ctx = workflow_data.get("runtime_context", {})
                if plan_obj:
                    engine = WorkflowEngine(tool_dispatcher=_dispatch_tool_for_approval)
                    run_result = engine.run(plan=plan_obj, runtime_context=runtime_ctx, max_retries=1)
                    run_result_data = {
                        "plan_id": plan_obj.plan_id,
                        "intent": plan_obj.intent,
                        "nodes_executed": len(run_result.node_results),
                        "nodes_total": len(plan_obj.nodes),
                        "has_errors": any(r.error for r in run_result.node_results.values()),
                        "results_summary": [
                            {"node_id": nid, "status": r.status.value, "output": str(r.output)[:200] if r.output else None}
                            for nid, r in list(run_result.node_results.items())[:5]
                        ],
                    }
                    approval_service.remove_pending_workflow(actual_request_id)

            response_data = {
                "status": "approved",
                "workflow_executed": workflow_data is not None,
            }
            if run_result_data:
                response_data["workflow_result"] = run_result_data

            return jsonify({
                "success": True,
                "message": "审批已通过" + ("，工作流已执行" if workflow_data else ""),
                "data": response_data
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "审批失败"
            }), 400

    except Exception as e:
        logger.exception(f"审批失败：{e}")
        return jsonify({
            "success": False,
            "message": f"审批失败：{str(e)}"
        }), 500


def _dispatch_tool_for_approval(node: Any, runtime_context: Dict[str, Any]) -> Any:
    """审批通过后用于执行工作流节点的工具分发器"""
    from app.application.workflow.engine import NodeExecutionResult
    tool_id = node.tool_id
    action = node.action
    params = node.params or {}

    try:
        from app.application.ai_chat_app_service import AIChatApplicationService
        service = AIChatApplicationService()
        dispatch_method = getattr(service, f"_dispatch_{tool_id}", None)
        if dispatch_method:
            result = dispatch_method(action=action, params=params, context=runtime_context)
            return NodeExecutionResult(
                status="completed",
                output=result.get("data") or result.get("response", {}),
                error=None,
                duration_ms=0,
            )

        logger.warning(f"审批工作流中未找到工具分发器: {tool_id}")
        return NodeExecutionResult(
            status="skipped",
            output={},
            error=f"工具 {tool_id} 未实现",
            duration_ms=0,
        )
    except Exception as e:
        logger.exception(f"审批工作流节点执行失败: {tool_id}.{action}")
        return NodeExecutionResult(
            status="failed",
            output={},
            error=str(e),
            duration_ms=0,
        )


@ai_chat_bp.route("/approval/reject", methods=["POST"])
def reject_request():
    """
    审批拒绝
    """
    try:
        payload = request.get_json() or {}
        request_id = payload.get("request_id") or ""
        plan_id = payload.get("plan_id") or ""
        comment = payload.get("comment") or ""

        from app.application.workflow import get_approval_service
        approval_service = get_approval_service()

        if request_id:
            success = approval_service.reject(request_id, comment)
        elif plan_id:
            pending_req = approval_service.get_pending_request_by_plan(plan_id)
            if not pending_req:
                return jsonify({
                    "success": False,
                    "message": "没有待审批的请求"
                }), 404
            success = approval_service.reject(pending_req.request_id, comment)
        else:
            return jsonify({
                "success": False,
                "message": "缺少 request_id 或 plan_id"
            }), 400

        if success:
            return jsonify({
                "success": True,
                "message": "审批已拒绝",
                "data": {"status": "rejected"}
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "审批拒绝失败"
            }), 400

    except Exception as e:
        logger.exception(f"审批拒绝失败：{e}")
        return jsonify({
            "success": False,
            "message": f"审批拒绝失败：{str(e)}"
        }), 500


@ai_chat_bp.route("/approval/pending", methods=["GET"])
def get_pending_approvals():
    """
    获取当前待审批请求
    """
    try:
        from app.application.workflow import get_approval_service
        approval_service = get_approval_service()

        all_pending = []
        for req in approval_service._pending_requests.values():
            if req.status.value == "pending":
                all_pending.append({
                    "request_id": req.request_id,
                    "plan_id": req.plan_id,
                    "node_id": req.node_id,
                    "tool_id": req.tool_id,
                    "action": req.action,
                    "params": req.params,
                    "status": req.status.value,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                })

        return jsonify({
            "success": True,
            "message": "获取成功",
            "data": {"pending_approvals": all_pending}
        }), 200

    except Exception as e:
        logger.exception(f"获取待审批请求失败：{e}")
        return jsonify({
            "success": False,
            "message": f"获取失败：{str(e)}"
        }), 500


@ai_chat_bp.route("/config/approval", methods=["GET"])
def get_approval_config():
    """
    获取审批配置
    """
    try:
        from resources.config.approval_config import get_approval_config
        config = get_approval_config()
        return jsonify({
            "success": True,
            "message": "获取成功",
            "enabled": config.enabled,
            "rules": config.rules
        }), 200
    except Exception as e:
        logger.exception(f"获取审批配置失败：{e}")
        return jsonify({
            "success": False,
            "message": f"获取失败：{str(e)}"
        }), 500


@ai_chat_bp.route("/config/approval", methods=["POST"])
def save_approval_config():
    """
    保存审批配置
    """
    try:
        payload = request.get_json() or {}
        enabled = payload.get("enabled", True)
        rules = payload.get("rules", [])

        from resources.config.approval_config import get_approval_config
        config = get_approval_config()
        config.enabled = enabled
        config.rules = rules
        config.save()

        from app.application.workflow import reload_approval_service
        reload_approval_service()

        return jsonify({
            "success": True,
            "message": "保存成功"
        }), 200
    except Exception as e:
        logger.exception(f"保存审批配置失败：{e}")
        return jsonify({
            "success": False,
            "message": f"保存失败：{str(e)}"
        }), 500