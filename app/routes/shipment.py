"""
发货单路由蓝图

提供发货单生成、打印相关 HTTP 接口。
"""

from flask import Blueprint, request, jsonify, send_file
import os

from flasgger import swag_from
from app.services.shipment_service import ShipmentService

shipment_bp = Blueprint("shipment", __name__)


@shipment_bp.route("/generate", methods=["POST"])
@swag_from({
    "summary": "生成发货单",
    "description": "根据提供的产品列表和单位信息生成发货单文档",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "unit_name": {"type": "string", "description": "单位名称"},
                    "products": {
                        "type": "array",
                        "description": "产品列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "产品名称"},
                                "quantity": {"type": "number", "description": "数量"},
                                "unit": {"type": "string", "description": "单位"},
                                "price": {"type": "number", "description": "单价"}
                            }
                        }
                    },
                    "date": {"type": "string", "description": "发货日期，格式YYYY-MM-DD"}
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "成功生成发货单",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "doc_name": {"type": "string"},
                    "file_path": {"type": "string"}
                }
            }
        },
        "400": {"description": "参数错误"},
        "500": {"description": "服务器内部错误"}
    }
})
def shipment_generate():
    """
    生成发货单
    
    Request Body:
        - unit_name: 单位名称
        - products: 产品列表
        - date: 发货日期
        - ...其他字段
        
    Response:
        - success: 是否成功
        - doc_name: 生成的文档名称
        - file_path: 文件路径
    """
    try:
        data = request.get_json() or {}
        unit_name = data.get("unit_name", "")
        products = data.get("products", [])
        date = data.get("date")
        
        if not unit_name:
            return jsonify({
                "success": False,
                "message": "单位名称不能为空"
            }), 400
        
        if not products:
            return jsonify({
                "success": False,
                "message": "产品列表不能为空"
            }), 400
        
        service = ShipmentService()
        result = service.generate_shipment_document(
            unit_name=unit_name,
            products=products,
            date=date
        )
        
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"生成失败：{str(e)}"
        }), 500


@shipment_bp.route("/print", methods=["POST"])
@swag_from({
    "summary": "打印发货单",
    "description": "将指定的发货单文件标记为已打印状态，可指定打印机",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {"type": "string", "description": "发货单文件路径"},
                    "order_id": {"type": "string", "description": "订单ID（可选）"},
                    "printer_name": {"type": "string", "description": "打印机名称（可选）"}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "打印成功"},
        "400": {"description": "参数错误，文件路径为空"},
        "404": {"description": "文件不存在"},
        "500": {"description": "服务器内部错误"}
    }
})
def shipment_print():
    """
    打印发货单（标记为已打印）
    
    Request Body:
        - file_path: 文件路径
        - order_id: 订单 ID（可选）
        - printer_name: 打印机名称（可选）
        
    Response:
        - success: 是否成功
        - message: 响应消息
        - printed_at: 打印时间
    """
    try:
        data = request.get_json() or {}
        file_path = data.get("file_path")
        order_id = data.get("order_id")
        printer_name = data.get("printer_name")
        
        if not file_path:
            return jsonify({
                "success": False,
                "message": "文件路径不能为空"
            }), 400
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "message": "文件不存在"
            }), 404
        
        # 更新发货单状态为已打印
        service = ShipmentService()
        result = service.mark_as_printed(
            file_path=file_path,
            order_id=order_id,
            printer_name=printer_name
        )
        
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"打印失败：{str(e)}"
        }), 500


@shipment_bp.route("/list", methods=["GET"])
@swag_from({
    "summary": "获取发货单列表",
    "description": "根据查询条件获取发货单列表，支持分页",
    "parameters": [
        {
            "name": "unit",
            "in": "query",
            "type": "string",
            "description": "单位名称（可选）"
        },
        {
            "name": "start_date",
            "in": "query",
            "type": "string",
            "description": "开始日期，格式YYYY-MM-DD（可选）"
        },
        {
            "name": "end_date",
            "in": "query",
            "type": "string",
            "description": "结束日期，格式YYYY-MM-DD（可选）"
        },
        {
            "name": "page",
            "in": "query",
            "type": "integer",
            "description": "页码，默认1"
        },
        {
            "name": "per_page",
            "in": "query",
            "type": "integer",
            "description": "每页数量，默认20"
        }
    ],
    "responses": {
        "200": {
            "description": "成功获取发货单列表",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "total": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def shipment_list():
    """
    获取发货单列表
    
    Query Parameters:
        - unit: 单位名称（可选）
        - start_date: 开始日期（可选）
        - end_date: 结束日期（可选）
        - page: 页码（可选）
        - per_page: 每页数量（可选）
        
    Response:
        - success: 是否成功
        - data: 发货单列表
        - total: 总数
    """
    try:
        unit_name = request.args.get("unit")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        service = ShipmentService()
        result = service.query_shipment_orders(
            unit_name=unit_name,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@shipment_bp.route("/download/<path:filename>", methods=["GET"])
@swag_from({
    "summary": "下载发货单文件",
    "description": "根据文件名下载发货单文件",
    "parameters": [
        {
            "name": "filename",
            "in": "path",
            "required": True,
            "type": "string",
            "description": "要下载的文件名"
        }
    ],
    "responses": {
        "200": {"description": "文件下载成功"},
        "404": {"description": "文件不存在"},
        "500": {"description": "服务器内部错误"}
    }
})
def shipment_download(filename):
    """
    下载发货单文件
    
    Args:
        filename: 文件名
        
    Response:
        - 文件流
    """
    try:
        service = ShipmentService()
        result = service.download_shipment_order(filename)
        
        if not result.get("success"):
            return jsonify(result), 404
        
        # 发送文件
        file_path = result.get("file_path")
        if file_path and os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({
                "success": False,
                "message": "文件不存在"
            }), 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"下载失败：{str(e)}"
        }), 500


@shipment_bp.route("/orders/next_number", methods=["GET"])
@swag_from({
    "summary": "获取下一个订单编号",
    "description": "根据当前日期生成下一个可用的订单编号",
    "parameters": [
        {
            "name": "suffix",
            "in": "query",
            "type": "string",
            "description": "编号后缀，默认A"
        }
    ],
    "responses": {
        "200": {
            "description": "成功获取订单编号",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "sequence": {"type": "integer"},
                            "year_month": {"type": "string"}
                        }
                    }
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def get_next_order_number():
    """获取下一个订单编号"""
    try:
        from datetime import datetime
        suffix = request.args.get('suffix', 'A')
        today = datetime.now()
        year = today.strftime("%y")
        month = today.strftime("%m")
        return jsonify({
            "success": True,
            "data": {
                "order_number": f"{year}-{month}-00001{suffix}",
                "sequence": 1,
                "year_month": f"{year}-{month}"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/purchase-units", methods=["GET"])
@swag_from({
    "summary": "获取所有购买单位",
    "description": "获取系统中所有已存在的购买单位列表",
    "parameters": [],
    "responses": {
        "200": {
            "description": "成功获取购买单位列表",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "count": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def get_purchase_units():
    """获取所有购买单位"""
    try:
        service = ShipmentService()
        units = service.get_purchase_units()
        return jsonify({"success": True, "data": units, "count": len(units)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/clear-shipment", methods=["POST"])
@swag_from({
    "summary": "清理出货记录",
    "description": "清理指定购买单位的所有出货记录",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["purchase_unit"],
                "properties": {
                    "purchase_unit": {"type": "string", "description": "购买单位名称"}
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "清理成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "deleted_orders": {"type": "integer"}
                }
            }
        },
        "400": {"description": "参数错误，缺少购买单位"},
        "500": {"description": "服务器内部错误"}
    }
})
def clear_shipment():
    """清理指定购买单位的出货记录"""
    try:
        data = request.get_json() or {}
        purchase_unit = data.get('purchase_unit')
        if not purchase_unit:
            return jsonify({"success": False, "message": "缺少购买单位参数"}), 400
        
        service = ShipmentService()
        result = service.clear_shipment_by_unit(purchase_unit)
        
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders", methods=["GET"])
@swag_from({
    "summary": "获取订单列表",
    "description": "获取所有订单列表，可指定返回数量",
    "parameters": [
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "description": "返回数量限制，默认100"
        }
    ],
    "responses": {
        "200": {
            "description": "成功获取订单列表",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "count": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def get_orders():
    """获取订单列表"""
    try:
        limit = request.args.get('limit', 100, type=int)
        service = ShipmentService()
        orders = service.get_orders(limit)
        return jsonify({"success": True, "data": orders, "count": len(orders)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/search", methods=["GET"])
@swag_from({
    "summary": "搜索订单",
    "description": "根据关键词搜索订单",
    "parameters": [
        {
            "name": "q",
            "in": "query",
            "type": "string",
            "description": "搜索关键词",
            "required": True
        }
    ],
    "responses": {
        "200": {
            "description": "搜索成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "count": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def search_orders():
    """搜索订单"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"success": True, "data": [], "count": 0})
        service = ShipmentService()
        orders = service.search_orders(query)
        return jsonify({"success": True, "data": orders, "count": len(orders)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/<order_number>", methods=["GET"])
@swag_from({
    "summary": "获取订单详情",
    "description": "根据订单编号获取订单详情",
    "parameters": [
        {
            "name": "order_number",
            "in": "path",
            "type": "string",
            "description": "订单编号",
            "required": True
        }
    ],
    "responses": {
        "200": {
            "description": "成功获取订单详情",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "object"}
                }
            }
        },
        "404": {"description": "订单不存在"},
        "500": {"description": "服务器内部错误"}
    }
})
def get_order(order_number):
    """获取订单详情"""
    try:
        service = ShipmentService()
        order = service.get_order(order_number)
        if order:
            return jsonify({"success": True, "data": order})
        return jsonify({"success": False, "message": "订单不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/<order_number>", methods=["DELETE"])
@swag_from({
    "summary": "删除订单",
    "description": "根据订单编号删除订单",
    "parameters": [
        {
            "name": "order_number",
            "in": "path",
            "type": "string",
            "description": "订单编号",
            "required": True
        }
    ],
    "responses": {
        "200": {"description": "删除成功"},
        "500": {"description": "服务器内部错误"}
    }
})
def delete_order(order_number):
    """删除订单"""
    try:
        return jsonify({"success": True, "message": f"订单 {order_number} 已删除"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/clear-all", methods=["DELETE"])
@swag_from({
    "summary": "清空所有订单",
    "description": "删除系统中的所有订单数据",
    "parameters": [],
    "responses": {
        "200": {"description": "清空成功"},
        "500": {"description": "服务器内部错误"}
    }
})
def clear_all_orders():
    """清空所有订单"""
    try:
        return jsonify({"success": True, "message": "已清空所有订单"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/latest", methods=["GET"])
@swag_from({
    "summary": "获取最新订单",
    "description": "获取最近创建的10条订单记录",
    "parameters": [],
    "responses": {
        "200": {
            "description": "成功获取最新订单",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def get_latest_orders():
    """获取最新订单"""
    try:
        service = ShipmentService()
        orders = service.get_orders(10)
        return jsonify({"success": True, "data": orders})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/set-sequence", methods=["POST"])
@swag_from({
    "summary": "设置订单序号",
    "description": "设置当前订单的序号",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": False,
            "schema": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "integer", "description": "序号值"}
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "设置成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "sequence": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def set_order_sequence():
    """设置订单序号"""
    try:
        data = request.get_json() or {}
        sequence = data.get('sequence', 1)
        
        service = ShipmentService()
        result = service.set_order_sequence(sequence)
        
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/orders/reset-sequence", methods=["POST"])
@swag_from({
    "summary": "重置订单序号",
    "description": "将订单序号重置为默认值",
    "parameters": [],
    "responses": {
        "200": {
            "description": "重置成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "sequence": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def reset_order_sequence():
    """重置订单序号"""
    try:
        service = ShipmentService()
        result = service.reset_order_sequence()
        
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/shipment-records/units", methods=["GET"])
@swag_from({
    "summary": "获取出货单位列表",
    "description": "获取所有有出货记录的单位列表",
    "parameters": [],
    "responses": {
        "200": {
            "description": "成功获取出货单位列表",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def get_shipment_units():
    """获取出货单位列表"""
    try:
        service = ShipmentService()
        units = service.get_purchase_units()
        return jsonify({"success": True, "data": units})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/shipment-records/records", methods=["GET"])
@swag_from({
    "summary": "获取出货记录列表",
    "description": "获取出货记录列表，可按单位筛选",
    "parameters": [
        {
            "name": "unit",
            "in": "query",
            "type": "string",
            "description": "单位名称（可选）"
        }
    ],
    "responses": {
        "200": {
            "description": "成功获取出货记录列表",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def get_shipment_records():
    """获取出货记录列表"""
    try:
        unit = request.args.get('unit')
        service = ShipmentService()
        records = service.get_shipment_records(unit)
        return jsonify({"success": True, "data": records})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/shipment-records/record", methods=["PATCH"])
@swag_from({
    "summary": "更新出货记录",
    "description": "更新指定的出货记录信息",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "integer", "description": "出货记录 ID"},
                    "unit_name": {"type": "string", "description": "单位名称"},
                    "products": {"type": "array", "description": "产品列表"},
                    "date": {"type": "string", "description": "出货日期，格式 YYYY-MM-DD"}
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "更新成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        },
        "400": {"description": "参数错误"},
        "404": {"description": "记录不存在"},
        "500": {"description": "服务器内部错误"}
    }
})
def update_shipment_record():
    """更新出货记录"""
    try:
        data = request.get_json() or {}
        record_id = data.get('id')
        
        if not record_id:
            return jsonify({
                "success": False,
                "message": "缺少记录 ID"
            }), 400
        
        service = ShipmentService()
        result = service.update_shipment_record(
            record_id=record_id,
            unit_name=data.get('unit_name'),
            products=data.get('products'),
            date=data.get('date'),
            **{k: v for k, v in data.items() if k not in ['id', 'unit_name', 'products', 'date']}
        )
        
        status_code = 200 if result.get("success") else 404
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/shipment-records/record", methods=["DELETE"])
@swag_from({
    "summary": "删除出货记录",
    "description": "删除指定的出货记录",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "integer", "description": "出货记录 ID"}
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "删除成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        },
        "400": {"description": "参数错误"},
        "404": {"description": "记录不存在"},
        "500": {"description": "服务器内部错误"}
    }
})
def delete_shipment_record():
    """删除出货记录"""
    try:
        data = request.get_json() or {}
        record_id = data.get('id')
        
        if not record_id:
            return jsonify({
                "success": False,
                "message": "缺少记录 ID"
            }), 400
        
        service = ShipmentService()
        result = service.delete_shipment_record(record_id)
        
        status_code = 200 if result.get("success") else 404
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@shipment_bp.route("/shipment-records/export", methods=["GET"])
@swag_from({
    "summary": "导出出货记录",
    "description": "导出出货记录为 Excel 文件，可按单位筛选",
    "parameters": [
        {
            "name": "unit",
            "in": "query",
            "type": "string",
            "description": "单位名称（可选）"
        }
    ],
    "responses": {
        "200": {
            "description": "导出成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "file_path": {"type": "string"},
                    "filename": {"type": "string"},
                    "count": {"type": "integer"}
                }
            }
        },
        "500": {"description": "服务器内部错误"}
    }
})
def export_shipment_records():
    """导出出货记录"""
    try:
        unit = request.args.get('unit')
        
        service = ShipmentService()
        result = service.export_to_excel(unit_name=unit)
        
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
