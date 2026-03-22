"""
AI助手接口兼容层（XCAGI 后端）。

目标：在保持 XCAGI 现有路由不变的前提下，补齐 AI助手/app_api.py 常用接口路径与返回结构，
以便 XCAGI 前端（以及旧版前端/脚本）可以直接调用。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from app.application import ShipmentApplicationService
from app.bootstrap import get_shipment_app_service
from app.db.models import Product, PurchaseUnit, ShipmentRecord
from app.db.session import get_db
from app.infrastructure.repositories.customer_repository_impl import get_customers_session

printer_service = None

def get_printer_svc():
    global printer_service
    if printer_service is None:
        from app.services import get_printer_service
        printer_service = get_printer_service()
    return printer_service

logger = logging.getLogger(__name__)

ai_assistant_compat_bp = Blueprint("ai_assistant_compat", __name__)


def get_shipment_service():
    return get_shipment_app_service()


def _json_success(data: Any = None, **kwargs):
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload)


def _json_fail(message: str, status: int = 400, **kwargs):
    payload = {"success": False, "message": message}
    payload.update(kwargs)
    return jsonify(payload), status


def _distinct_product_names(keyword: Optional[str] = None) -> List[str]:
    keyword_norm = (keyword or "").strip()
    with get_db() as db:
        q = db.query(Product.name).filter(Product.is_active == 1)
        if keyword_norm:
            q = q.filter(Product.name.like(f"%{keyword_norm}%"))
        rows = q.distinct().order_by(Product.name.asc()).all()
        return [r[0] for r in rows if r and r[0]]


@ai_assistant_compat_bp.route("/health", methods=["GET"])
def health():
    """兼容 AI助手: GET /health"""
    return _json_success({"status": "ok", "timestamp": datetime.now().isoformat()})


@ai_assistant_compat_bp.route("/api/generate", methods=["POST"])
def ai_generate_document():
    """
    兼容 AI助手: POST /api/generate
    Body: {"order_text": "...", "template_name": "...", ...}
    """
    data = request.get_json(silent=True) or {}
    order_text = (data.get("order_text") or "").strip()
    template_name = data.get("template_name")

    if not order_text:
        return _json_fail("请输入订单信息", 400)

    # 复用 XCAGI 的订单文本解析与发货单生成（与 tools.execute shipment_generate 一致）
    try:
        from app.routes.tools import _parse_order_text  # 本项目内部工具解析器

        parsed = _parse_order_text(order_text)
        if not parsed.get("success"):
            return _json_fail(parsed.get("message", "订单解析失败"), 400)

        unit_name = parsed.get("unit_name", "").strip()
        products = parsed.get("products") or []
        if not unit_name or not products:
            return _json_fail("订单解析结果为空", 400)

        app_service = get_shipment_service()
        result = app_service.generate_shipment_document(
            unit_name=unit_name,
            products=products,
            template_name=template_name,
        )

        if not result.get("success"):
            return jsonify(result), 500

        file_path = result.get("file_path")
        doc_name = result.get("doc_name") or (os.path.basename(file_path) if file_path else None)
        download_url = f"/api/shipment/download/{doc_name}" if doc_name else None

        # AI助手 常见返回字段：success/message + 生成结果
        return _json_success(
            {
                "doc_name": doc_name,
                "file_path": file_path,
                "download_url": download_url,
                "order_number": result.get("order_number"),
                "total_amount": result.get("total_amount"),
                "total_quantity": result.get("total_quantity"),
            },
            message="发货单生成成功",
            filename=doc_name,
            file_path=file_path,
        )
    except Exception as e:
        logger.error("兼容 /api/generate 失败: %s", e, exc_info=True)
        return _json_fail(f"生成失败: {str(e)}", 500)


@ai_assistant_compat_bp.route("/orders/next_number", methods=["GET"])
def ai_orders_next_number():
    """兼容 AI助手: GET /orders/next_number"""
    try:
        suffix = request.args.get("suffix", "A")
        today = datetime.now()
        year = today.strftime("%y")
        month = today.strftime("%m")

        # 在 XCAGI 侧用 shipment_records 的当月数量近似做序号
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 下个月第一天
        next_month = (start + timedelta(days=32)).replace(day=1)
        with get_db() as db:
            count = (
                db.query(ShipmentRecord)
                .filter(ShipmentRecord.created_at >= start, ShipmentRecord.created_at < next_month)
                .count()
            )
        next_sequence = int(count) + 1
        order_number = f"{year}-{month}-{next_sequence:05d}{suffix}"

        return _json_success(
            {
                "order_number": order_number,
                "sequence": next_sequence,
                "year_month": f"{year}-{month}",
            }
        )
    except Exception as e:
        logger.error("获取订单编号失败: %s", e, exc_info=True)
        return _json_fail(f"获取订单编号失败：{str(e)}", 500)


# -------------------- 订单 API 兼容层 --------------------

@ai_assistant_compat_bp.route("/api/orders", methods=["GET", "DELETE"])
@ai_assistant_compat_bp.route("/api/orders/", methods=["DELETE"])
def ai_orders_list():
    app_service = get_shipment_service()
    if request.method == "DELETE":
        # 兼容旧前端：DELETE /api/orders 或 /api/orders/
        result = app_service.clear_all_orders()
        return jsonify(result), (200 if result.get("success") else 500)

    limit = int(request.args.get("limit", 100))
    orders = app_service.get_orders(limit=limit) or []
    result = {"success": True, "data": orders, "count": len(orders)}
    return jsonify(result), 200


@ai_assistant_compat_bp.route("/api/orders/latest", methods=["GET"])
def ai_orders_latest():
    app_service = get_shipment_service()
    orders = app_service.get_orders(limit=10) or []
    result = {"success": True, "data": orders, "count": len(orders)}
    return jsonify(result), 200


@ai_assistant_compat_bp.route("/api/orders/search", methods=["GET"])
def ai_orders_search():
    q = (request.args.get("q") or "").strip()
    app_service = get_shipment_service()
    rows = app_service.search_orders(q) if q else []
    return _json_success(rows, count=len(rows))


@ai_assistant_compat_bp.route("/api/orders/<order_number>", methods=["GET"])
def ai_orders_get(order_number: str):
    # XCAGI 的 shipment_records 主键是 int；这里尽量兼容
    try:
        order_id = int(order_number)
    except Exception:
        return _json_fail("订单不存在", 404)

    app_service = get_shipment_service()
    order = app_service.get_order(str(order_id))
    if not order:
        return _json_fail("订单不存在", 404)
    return _json_success(order)


@ai_assistant_compat_bp.route("/api/orders/set-sequence", methods=["POST"])
def ai_orders_set_sequence():
    data = request.get_json(silent=True) or {}
    sequence = int(data.get("sequence", 1))
    app_service = get_shipment_service()
    return jsonify(app_service.set_order_sequence(sequence))


@ai_assistant_compat_bp.route("/api/orders/reset-sequence", methods=["POST"])
def ai_orders_reset_sequence():
    app_service = get_shipment_service()
    return jsonify(app_service.reset_order_sequence())


@ai_assistant_compat_bp.route("/api/orders/purchase-units", methods=["GET"])
def ai_orders_purchase_units():
    app_service = get_shipment_service()
    units = app_service.get_purchase_units()
    return _json_success(units, count=len(units))


@ai_assistant_compat_bp.route("/api/orders/clear-shipment", methods=["POST"])
def ai_orders_clear_shipment():
    data = request.get_json(silent=True) or {}
    purchase_unit = (data.get("purchase_unit") or "").strip()
    if not purchase_unit:
        return _json_fail("缺少购买单位参数", 400)
    app_service = get_shipment_service()
    result = app_service.clear_shipment_by_unit(purchase_unit)
    return jsonify(result), (200 if result.get("success") else 500)


@ai_assistant_compat_bp.route("/api/orders/clear-all", methods=["DELETE"])
def ai_orders_clear_all():
    """兼容前端: DELETE /api/orders/clear-all"""
    app_service = get_shipment_service()
    result = app_service.clear_all_orders()
    return jsonify(result), (200 if result.get("success") else 500)


# -------------------- 出货记录（旧前端路径兼容） --------------------

@ai_assistant_compat_bp.route("/api/shipment-records/units", methods=["GET"])
def ai_shipment_records_units():
    """兼容前端: GET /api/shipment-records/units"""
    app_service = get_shipment_service()
    units = app_service.get_purchase_units()
    return _json_success(units, count=len(units))


@ai_assistant_compat_bp.route("/api/shipment-records/records", methods=["GET"])
def ai_shipment_records_records():
    """兼容前端: GET /api/shipment-records/records?unit=..."""
    unit = request.args.get("unit")
    app_service = get_shipment_service()
    rows = app_service.get_shipment_records(unit_name=unit)
    return _json_success(rows, count=len(rows))


# -------------------- 购买单位 / 产品名 兼容层 --------------------

@ai_assistant_compat_bp.route("/api/purchase_units", methods=["GET"])
def ai_purchase_units_get():
    session = get_customers_session()
    try:
        units = session.query(PurchaseUnit).filter(PurchaseUnit.is_active == True).order_by(PurchaseUnit.unit_name.asc()).all()
        data = [
            {
                "id": u.id,
                "unit_name": u.unit_name,
                "contact_person": u.contact_person or "",
                "contact_phone": u.contact_phone or "",
                "address": u.address or "",
                "is_active": 1,
            }
            for u in units
        ]
        return _json_success(data, count=len(data))
    finally:
        session.close()


@ai_assistant_compat_bp.route("/api/purchase_units", methods=["POST"])
def ai_purchase_units_create():
    data = request.get_json(silent=True) or {}
    unit_name = (data.get("unit_name") or data.get("name") or "").strip()
    if not unit_name:
        return _json_fail("单位名称不能为空", 400)

    session = get_customers_session()
    try:
        exists = session.query(PurchaseUnit).filter(PurchaseUnit.unit_name == unit_name).first()
        if exists:
            return _json_success(
                {"id": exists.id, "unit_name": exists.unit_name},
                message="已存在",
            )

        unit = PurchaseUnit(
            unit_name=unit_name,
            contact_person=data.get("contact_person") or "",
            contact_phone=data.get("contact_phone") or "",
            address=data.get("address") or "",
        )
        session.add(unit)
        session.commit()
        return _json_success({"id": unit.id, "unit_name": unit.unit_name}, message="添加成功")
    finally:
        session.close()


@ai_assistant_compat_bp.route("/api/purchase_units/<int:unit_id>", methods=["PUT"])
def ai_purchase_units_update(unit_id: int):
    data = request.get_json(silent=True) or {}
    session = get_customers_session()
    try:
        unit = session.query(PurchaseUnit).filter(PurchaseUnit.id == unit_id).first()
        if not unit:
            return _json_fail("购买单位不存在", 404)
        if "unit_name" in data and (data.get("unit_name") or "").strip():
            unit.unit_name = data["unit_name"].strip()
        for k in ["contact_person", "contact_phone"]:
            if k in data:
                setattr(unit, k, data.get(k))
        if "address" in data:
            unit.address = data.get(k)
        session.commit()
        return _json_success({"id": unit.id, "unit_name": unit.unit_name}, message="更新成功")
    finally:
        session.close()


@ai_assistant_compat_bp.route("/api/purchase_units/<int:unit_id>", methods=["DELETE"])
def ai_purchase_units_delete(unit_id: int):
    session = get_customers_session()
    try:
        unit = session.query(PurchaseUnit).filter(PurchaseUnit.id == unit_id).first()
        if not unit:
            return _json_fail("购买单位不存在", 404)
        session.delete(unit)
        session.commit()
        return _json_success(message="删除成功")
    finally:
        session.close()


@ai_assistant_compat_bp.route("/api/purchase_units/by_name/<unit_name>", methods=["GET"])
def ai_purchase_units_by_name(unit_name: str):
    name = (unit_name or "").strip()
    session = get_customers_session()
    try:
        unit = session.query(PurchaseUnit).filter(PurchaseUnit.unit_name == name).first()
        if not unit:
            return _json_fail("购买单位不存在", 404)
        return _json_success(
            {
                "id": unit.id,
                "unit_name": unit.unit_name,
                "contact_person": unit.contact_person or "",
                "contact_phone": unit.contact_phone or "",
                "address": unit.address or "",
                "is_active": 1,
            }
        )
    finally:
        session.close()


@ai_assistant_compat_bp.route("/api/product_names", methods=["GET"])
def ai_product_names():
    names = _distinct_product_names()
    return _json_success(names, count=len(names))


@ai_assistant_compat_bp.route("/api/product_names/search", methods=["GET"])
def ai_product_names_search():
    keyword = request.args.get("keyword", "")
    names = _distinct_product_names(keyword=keyword)
    return _json_success(names, count=len(names))


@ai_assistant_compat_bp.route("/api/product_names/by_unit/<int:unit_id>", methods=["GET"])
def ai_product_names_by_unit(unit_id: int):
    # XCAGI 当前产品表不区分 unit_id，这里返回全量以保证兼容
    names = _distinct_product_names()
    return _json_success(names, count=len(names), unit_id=unit_id)


@ai_assistant_compat_bp.route("/api/product_names/by_unit_and_name", methods=["GET"])
def ai_product_by_unit_and_name():
    # AI助手: 通过 unit_id + name 获取产品详情。XCAGI 侧先忽略 unit_id，按名称取第一条。
    name = (request.args.get("name") or "").strip()
    if not name:
        return _json_fail("缺少参数：name", 400)
    with get_db() as db:
        p = db.query(Product).filter(Product.name == name).first()
        if not p:
            return _json_fail("产品不存在", 404)
        return _json_success(
            {
                "id": p.id,
                "name": p.name,
                "model_number": p.model_number or "",
                "specification": p.specification or "",
                "price": float(p.price or 0.0),
                "description": p.description or "",
            }
        )


# -------------------- 打印 API 兼容层 --------------------

@ai_assistant_compat_bp.route("/api/printers", methods=["GET"])
def ai_printers():
    """
    兼容 AI助手: GET /api/printers
    返回 printers + classified + summary 结构（字段名尽量与 app_api.py 对齐）
    """
    base = get_printer_svc().get_printers()
    printers = base.get("printers") or []

    # 尝试分类：文档打印机优先选非标签关键字；标签打印机选包含关键字
    exclude_keywords = ["tsc", "ttp", "label", "标签", "thermal", "barcode", "zebra"]
    label_candidates = []
    doc_candidates = []
    for p in printers:
        name = (p.get("name") if isinstance(p, dict) else str(p)) or ""
        name_lower = name.lower()
        if any(k in name_lower for k in exclude_keywords):
            label_candidates.append(name)
        else:
            doc_candidates.append(name)

    document_printer_name = doc_candidates[0] if doc_candidates else None
    label_printer_name = label_candidates[0] if label_candidates else (printers[0].get("name") if printers and isinstance(printers[0], dict) else None)

    classified = {
        "document_printer": {
            "name": document_printer_name,
            "status": "未知" if document_printer_name else "未连接",
            "is_connected": bool(document_printer_name),
        },
        "label_printer": {
            "name": label_printer_name,
            "status": "未知" if label_printer_name else "未连接",
            "is_connected": bool(label_printer_name),
        },
    }
    summary = {
        "total_printers": len(printers),
        "document_printer_ready": bool(document_printer_name),
        "label_printer_ready": bool(label_printer_name),
        "all_ready": bool(document_printer_name) and bool(label_printer_name),
    }

    return jsonify(
        {
            "success": base.get("success", True),
            "printers": printers,
            "count": len(printers),
            "classified": classified,
            "summary": summary,
        }
    )


@ai_assistant_compat_bp.route("/api/print/diagnose", methods=["GET"])
def ai_print_diagnose():
    """兼容 AI助手: GET /api/print/diagnose（提供基础诊断信息）"""
    try:
        printers_resp = ai_printers().json  # type: ignore[attr-defined]
        # 兼容：ai_printers 可能不是 Response.json 可用，兜底直接调用 service
        if not isinstance(printers_resp, dict):
            printers_resp = get_printer_svc().get_printers()
        return jsonify({"success": True, "diagnostic": printers_resp})
    except Exception as e:
        logger.error("打印机诊断失败: %s", e, exc_info=True)
        return _json_fail(f"打印机诊断失败: {str(e)}", 500)


@ai_assistant_compat_bp.route("/api/print/<path:filename>", methods=["POST"])
def ai_print_file(filename: str):
    """
    兼容 AI助手: POST /api/print/<filename>
    Body: {"printer_name": "..."} 可选
    """
    data = request.get_json(silent=True) or {}
    printer_name = data.get("printer_name") or data.get("printer")

    from app.utils.path_utils import get_app_data_dir

    output_dir = os.path.join(get_app_data_dir(), "shipment_outputs")
    file_path = os.path.join(output_dir, filename)
    if not file_path or not os.path.exists(file_path):
        return _json_fail("文件不存在", 404)

    result = get_printer_svc().print_document(file_path, printer_name=printer_name)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@ai_assistant_compat_bp.route("/api/print-last", methods=["POST"])
def ai_print_last():
    """
    兼容 AI助手: POST /api/print-last
    XCAGI 没有“上一次打印文件”的全局状态；这里返回可读错误，保证前端不崩溃。
    """
    return _json_fail("XCAGI 未实现 print-last（请通过 /api/print/<filename> 打印指定文件）", 501)


@ai_assistant_compat_bp.route("/api/print/list_labels", methods=["GET"])
def ai_print_list_labels():
    """
    兼容 AI助手: GET /api/print/list_labels
    返回可见的标签文件列表（优先扫描项目根目录下的 PDF文件/ 目录）。
    """
    try:
        # 候选目录：
        # - XCAGI/PDF文件（本仓库常见）
        # - XCAGI/AI助手/PDF文件（兼容旧版）
        # - XCAGI/AI助手/outputs（若标签以图片输出）
        xcagi_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [
            os.path.join(xcagi_root, "PDF文件"),
            os.path.join(xcagi_root, "AI助手", "PDF文件"),
            os.path.join(xcagi_root, "AI助手", "outputs"),
        ]

        labels: List[Dict[str, str]] = []
        for d in candidates:
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                if name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
                    labels.append({"filename": name, "path": os.path.join(d, name)})

        labels.sort(key=lambda x: x["filename"])
        return _json_success(labels, count=len(labels))
    except Exception as e:
        logger.error("列出标签失败: %s", e, exc_info=True)
        return _json_fail(f"列出标签失败: {str(e)}", 500)


@ai_assistant_compat_bp.route("/api/print/pdf_labels", methods=["POST"])
def ai_print_pdf_labels():
    """兼容 AI助手: POST /api/print/pdf_labels（暂提供占位实现）"""
    return _json_fail("XCAGI 暂未实现 pdf_labels（请使用现有打印功能）", 501)


@ai_assistant_compat_bp.route("/api/print/single_label", methods=["POST"])
def ai_print_single_label():
    """兼容 AI助手: POST /api/print/single_label（暂提供占位实现）"""
    return _json_fail("XCAGI 暂未实现 single_label（请使用现有打印功能）", 501)


@ai_assistant_compat_bp.route("/api/tts", methods=["POST"])
def tts_fallback():
    """
    兼容前端专业模式：POST /api/tts
    使用 Edge TTS 生成音频（默认 zh-CN-XiaoxiaoNeural）并以 base64 data-uri 返回。
    若合成失败，则返回 200 + success=false，让前端自动回退到浏览器 SpeechSynthesis。
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "message": "text 不能为空", "data": {}}), 400

    speaker_id = data.get("speakerId")
    lang = (data.get("lang") or "zh").lower()
    voice = data.get("voice")
    rate = data.get("rate")
    pitch = data.get("pitch")

    try:
        from app.services import synthesize_to_data_uri

        payload = synthesize_to_data_uri(
            text=text,
            voice=voice,
            speaker_id=speaker_id,
            lang=lang,
            rate=rate,
            pitch=pitch,
        )

        return jsonify(
            {
                "success": True,
                "message": "ok",
                "data": {
                    "audioBase64": payload.get("audioBase64"),
                    "voice": payload.get("voice"),
                    "speakerId": speaker_id,
                    "lang": payload.get("lang") or lang,
                },
            }
        )
    except Exception as e:
        logger.warning("Edge TTS 不可用，回退浏览器语音: %s", e)
        return jsonify({"success": False, "message": "TTS 服务未启用，将使用浏览器语音", "data": {}})

