# -*- coding: utf-8 -*-
"""
库存管理路由蓝图

提供仓库、库位、库存等 HTTP 接口。
"""

from datetime import datetime

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from app.services.inventory_service import InventoryService

inventory_bp = Blueprint("inventory", __name__)


def get_inventory_service():
    return InventoryService()


@inventory_bp.route("/warehouses", methods=["GET"])
def get_warehouses():
    service = get_inventory_service()
    status = request.args.get("status")
    result = service.get_warehouses(status=status)
    return jsonify(result)


@inventory_bp.route("/warehouses/<int:warehouse_id>", methods=["GET"])
def get_warehouse(warehouse_id):
    service = get_inventory_service()
    result = service.get_warehouse(warehouse_id)
    return jsonify(result)


@inventory_bp.route("/warehouses", methods=["POST"])
def create_warehouse():
    service = get_inventory_service()
    data = request.get_json() or {}
    result = service.create_warehouse(data)
    return jsonify(result)


@inventory_bp.route("/warehouses/<int:warehouse_id>", methods=["PUT"])
def update_warehouse(warehouse_id):
    service = get_inventory_service()
    data = request.get_json() or {}
    result = service.update_warehouse(warehouse_id, data)
    return jsonify(result)


@inventory_bp.route("/warehouses/<int:warehouse_id>", methods=["DELETE"])
def delete_warehouse(warehouse_id):
    service = get_inventory_service()
    result = service.delete_warehouse(warehouse_id)
    return jsonify(result)


@inventory_bp.route("/locations", methods=["GET"])
def get_storage_locations():
    service = get_inventory_service()
    warehouse_id = request.args.get("warehouse_id", type=int)
    status = request.args.get("status")
    if not warehouse_id:
        return jsonify({"success": False, "message": "仓库ID不能为空"})
    result = service.get_storage_locations(warehouse_id=warehouse_id, status=status)
    return jsonify(result)


@inventory_bp.route("/locations", methods=["POST"])
def create_storage_location():
    service = get_inventory_service()
    data = request.get_json() or {}
    result = service.create_storage_location(data)
    return jsonify(result)


@inventory_bp.route("/", methods=["GET"])
def get_inventory():
    service = get_inventory_service()
    warehouse_id = request.args.get("warehouse_id", type=int)
    product_id = request.args.get("product_id", type=int)
    batch_no = request.args.get("batch_no")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    result = service.get_inventory(
        warehouse_id=warehouse_id,
        product_id=product_id,
        batch_no=batch_no,
        page=page,
        per_page=per_page
    )
    return jsonify(result)


@inventory_bp.route("/summary", methods=["GET"])
def get_inventory_summary():
    service = get_inventory_service()
    warehouse_id = request.args.get("warehouse_id", type=int)
    result = service.get_inventory_summary(warehouse_id=warehouse_id)
    return jsonify(result)


@inventory_bp.route("/in", methods=["POST"])
def inventory_in():
    service = get_inventory_service()
    data = request.get_json() or {}
    result = service.inventory_in(
        product_id=data.get("product_id"),
        warehouse_id=data.get("warehouse_id"),
        quantity=float(data.get("quantity", 0)),
        batch_no=data.get("batch_no"),
        location_id=data.get("location_id"),
        unit_price=float(data.get("unit_price")) if data.get("unit_price") else None,
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        operator=data.get("operator"),
        remark=data.get("remark")
    )
    return jsonify(result)


@inventory_bp.route("/out", methods=["POST"])
def inventory_out():
    service = get_inventory_service()
    data = request.get_json() or {}
    result = service.inventory_out(
        product_id=data.get("product_id"),
        warehouse_id=data.get("warehouse_id"),
        quantity=float(data.get("quantity", 0)),
        batch_no=data.get("batch_no"),
        location_id=data.get("location_id"),
        unit_price=float(data.get("unit_price")) if data.get("unit_price") else None,
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        operator=data.get("operator"),
        remark=data.get("remark")
    )
    return jsonify(result)


@inventory_bp.route("/transfer", methods=["POST"])
def inventory_transfer():
    service = get_inventory_service()
    data = request.get_json() or {}
    result = service.inventory_transfer(
        product_id=data.get("product_id"),
        from_warehouse_id=data.get("from_warehouse_id"),
        to_warehouse_id=data.get("to_warehouse_id"),
        quantity=float(data.get("quantity", 0)),
        batch_no=data.get("batch_no"),
        from_location_id=data.get("from_location_id"),
        to_location_id=data.get("to_location_id"),
        operator=data.get("operator"),
        remark=data.get("remark")
    )
    return jsonify(result)


@inventory_bp.route("/transactions", methods=["GET"])
def get_inventory_transactions():
    service = get_inventory_service()
    product_id = request.args.get("product_id", type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    transaction_type = request.args.get("transaction_type")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    result = service.get_inventory_transactions(
        product_id=product_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        per_page=per_page
    )
    return jsonify(result)


@inventory_bp.route("/inventory/alert", methods=["GET"])
def get_inventory_alert():
    service = get_inventory_service()
    result = service.get_inventory_alert()
    return jsonify(result)
