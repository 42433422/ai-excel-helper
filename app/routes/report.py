# -*- coding: utf-8 -*-
"""
报表路由蓝图

提供销售、库存、采购等统计报表 HTTP 接口。
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from app.services.report_service import ReportService

report_bp = Blueprint("report", __name__)


def get_report_service():
    return ReportService()


@report_bp.route("/sales", methods=["GET"])
def get_sales_report():
    service = get_report_service()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    group_by = request.args.get("group_by", "product")
    customer_id = request.args.get("customer_id", type=int)

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    result = service.get_sales_report(
        start_date=start_dt,
        end_date=end_dt,
        group_by=group_by,
        customer_id=customer_id
    )
    return jsonify(result)


@report_bp.route("/inventory", methods=["GET"])
def get_inventory_report():
    service = get_report_service()
    warehouse_id = request.args.get("warehouse_id", type=int)
    category = request.args.get("category")

    result = service.get_inventory_report(
        warehouse_id=warehouse_id,
        category=category
    )
    return jsonify(result)


@report_bp.route("/purchase", methods=["GET"])
def get_purchase_report():
    service = get_report_service()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    group_by = request.args.get("group_by", "supplier")

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    result = service.get_purchase_report(
        start_date=start_dt,
        end_date=end_dt,
        group_by=group_by
    )
    return jsonify(result)


@report_bp.route("/inventory/transactions", methods=["GET"])
def get_inventory_transaction_report():
    service = get_report_service()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    transaction_type = request.args.get("transaction_type")
    product_id = request.args.get("product_id", type=int)

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    result = service.get_inventory_transaction_report(
        start_date=start_dt,
        end_date=end_dt,
        transaction_type=transaction_type,
        product_id=product_id
    )
    return jsonify(result)


@report_bp.route("/dashboard", methods=["GET"])
def get_dashboard_summary():
    service = get_report_service()
    result = service.get_dashboard_summary()
    return jsonify(result)


@report_bp.route("/export", methods=["POST"])
def export_report():
    service = get_report_service()
    data = request.get_json() or {}
    report_type = data.get("report_type", "report")
    report_data = data.get("data", [])
    filename = data.get("filename", "report")

    result = service.export_to_excel(
        report_type=report_type,
        data=report_data,
        filename=filename
    )
    return jsonify(result)
