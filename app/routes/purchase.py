# -*- coding: utf-8 -*-
"""
采购管理路由蓝图

提供供应商、采购订单、采购入库等 HTTP 接口。
"""

from datetime import datetime

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from app.services.purchase_service import PurchaseService

purchase_bp = Blueprint("purchase", __name__)


def get_purchase_service():
    return PurchaseService()


@purchase_bp.route("/suppliers", methods=["GET"])
def get_suppliers():
    service = get_purchase_service()
    status = request.args.get("status")
    keyword = request.args.get("keyword")
    result = service.get_suppliers(status=status, keyword=keyword)
    return jsonify(result)


@purchase_bp.route("/suppliers/<int:supplier_id>", methods=["GET"])
def get_supplier(supplier_id):
    service = get_purchase_service()
    result = service.get_supplier(supplier_id)
    return jsonify(result)


@purchase_bp.route("/suppliers", methods=["POST"])
def create_supplier():
    service = get_purchase_service()
    data = request.get_json() or {}
    result = service.create_supplier(data)
    return jsonify(result)


@purchase_bp.route("/suppliers/<int:supplier_id>", methods=["PUT"])
def update_supplier(supplier_id):
    service = get_purchase_service()
    data = request.get_json() or {}
    result = service.update_supplier(supplier_id, data)
    return jsonify(result)


@purchase_bp.route("/suppliers/<int:supplier_id>", methods=["DELETE"])
def delete_supplier(supplier_id):
    service = get_purchase_service()
    result = service.delete_supplier(supplier_id)
    return jsonify(result)


@purchase_bp.route("/suppliers/summary", methods=["GET"])
def get_supplier_summary():
    service = get_purchase_service()
    result = service.get_supplier_summary()
    return jsonify(result)


@purchase_bp.route("/orders", methods=["GET"])
def get_purchase_orders():
    service = get_purchase_service()
    supplier_id = request.args.get("supplier_id", type=int)
    status = request.args.get("status")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    result = service.get_purchase_orders(
        supplier_id=supplier_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        per_page=per_page
    )
    return jsonify(result)


@purchase_bp.route("/orders/<int:order_id>", methods=["GET"])
def get_purchase_order(order_id):
    service = get_purchase_service()
    result = service.get_purchase_order(order_id)
    return jsonify(result)


@purchase_bp.route("/orders", methods=["POST"])
def create_purchase_order():
    service = get_purchase_service()
    data = request.get_json() or {}
    result = service.create_purchase_order(data)
    return jsonify(result)


@purchase_bp.route("/orders/<int:order_id>", methods=["PUT"])
def update_purchase_order(order_id):
    service = get_purchase_service()
    data = request.get_json() or {}
    result = service.update_purchase_order(order_id, data)
    return jsonify(result)


@purchase_bp.route("/orders/<int:order_id>/approve", methods=["POST"])
def approve_purchase_order(order_id):
    service = get_purchase_service()
    approver = request.args.get("approver", "system")
    result = service.approve_purchase_order(order_id, approver)
    return jsonify(result)


@purchase_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
def cancel_purchase_order(order_id):
    service = get_purchase_service()
    result = service.cancel_purchase_order(order_id)
    return jsonify(result)


@purchase_bp.route("/inbounds", methods=["GET"])
def get_purchase_inbounds():
    service = get_purchase_service()
    supplier_id = request.args.get("supplier_id", type=int)
    order_id = request.args.get("order_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    result = service.get_purchase_inbounds(
        supplier_id=supplier_id,
        order_id=order_id,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        per_page=per_page
    )
    return jsonify(result)


@purchase_bp.route("/inbounds", methods=["POST"])
def create_purchase_inbound():
    service = get_purchase_service()
    data = request.get_json() or {}
    result = service.create_purchase_inbound(data)
    return jsonify(result)


@purchase_bp.route("/summary", methods=["GET"])
def get_purchase_summary():
    service = get_purchase_service()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    result = service.get_purchase_summary(start_date=start_dt, end_date=end_dt)
    return jsonify(result)
