"""
购买单位路由蓝图

提供购买单位导入/导出相关 HTTP 接口。
"""

import os

from flasgger import swag_from
from flask import Blueprint, jsonify, request, send_file

from app.application import CustomerApplicationService, get_customer_app_service
from app.utils.json_safe import json_safe

customers_bp = Blueprint("customers", __name__)


def get_customer_service():
    """获取客户应用服务实例"""
    return get_customer_app_service()


@customers_bp.route("", methods=["GET"])
@customers_bp.route("/", methods=["GET"])
def customers_index():
    """
    客户列表接口（根路径）
    
    Query Parameters:
        - keyword: 搜索关键词（可选）
        - page: 页码（可选，默认 1）
        - per_page: 每页数量（可选，默认 20）
        
    Response:
        - success: 是否成功
        - data: 客户列表
        - total: 总数
        - page: 当前页
        - per_page: 每页数量
    """
    return customers_list()


@customers_bp.route("/import", methods=["GET", "POST"])
@swag_from({
    'summary': '购买单位导入',
    'description': '上传 Excel 文件导入购买单位数据',
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Excel 文件 (.xlsx 格式)'
        }
    ],
    'responses': {
        '200': {
            'description': '导入成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'updated': {'type': 'integer'},
                    'inserted': {'type': 'integer'},
                    'skipped': {'type': 'integer'}
                }
            }
        }
    }
})
def customers_import():
    """
    购买单位导入接口
    
    GET: 返回接口说明
    POST: 上传 Excel 文件进行导入
    
    Request POST:
        - file: Excel 文件（.xlsx 格式）
        - excel_file: Excel 文件（.xlsx 格式，备用字段名）
        
    Response:
        - success: 是否成功
        - message: 响应消息
        - updated: 更新的记录数
        - inserted: 新增的记录数
        - skipped: 跳过的记录数
    """
    if request.method == "GET":
        return jsonify({
            "success": True,
            "message": "购买单位导入接口，请使用 POST 上传 .xlsx 文件"
        })
    
    # 处理文件上传
    file = request.files.get("file") or request.files.get("excel_file")
    
    if not file or not file.filename:
        return jsonify({
            "success": False,
            "message": "未选择文件"
        }), 400
    
    # 调用服务层处理导入
    success, payload, status = import_customers_from_excel(file)
    
    return jsonify(payload), status


@customers_bp.route("/export", methods=["GET"])
def customers_export():
    """
    购买单位导出接口
    
    Query Parameters:
        - keyword: 搜索关键词（可选）
        
    Response:
        - Excel 文件下载
    """
    try:
        keyword = request.args.get("keyword")
        template_id = request.args.get("template_id")
        
        success, result, status = export_customers_to_excel(keyword=keyword, template_id=template_id)
        
        if not success:
            return jsonify(result), status
        
        # 发送文件
        file_path = result.get("file_path")
        if file_path and os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=result.get("filename", "购买单位导出.xlsx")
            )
        else:
            return jsonify({
                "success": False,
                "message": "生成的文件不存在"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"导出失败：{str(e)}"
        }), 500


@customers_bp.route("", methods=["POST"])
@customers_bp.route("/", methods=["POST"])
@swag_from({
    'summary': '创建单个客户',
    'description': '创建一个新的客户记录',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['customer_name'],
                'properties': {
                    'customer_name': {
                        'type': 'string',
                        'description': '客户名称',
                        'example': '七彩乐园'
                    },
                    'contact_person': {
                        'type': 'string',
                        'description': '联系人',
                        'example': '张三'
                    },
                    'contact_phone': {
                        'type': 'string',
                        'description': '联系电话',
                        'example': '13800138000'
                    },
                    'contact_address': {
                        'type': 'string',
                        'description': '联系地址',
                        'example': '某某市某某区某某路 123 号'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '创建成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'customer_name': {'type': 'string'},
                            'contact_person': {'type': 'string'},
                            'contact_phone': {'type': 'string'},
                            'contact_address': {'type': 'string'},
                            'created_at': {'type': 'string', 'format': 'date-time'},
                            'updated_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        '400': {
            'description': '请求参数错误'
        }
    }
})
def customers_create():
    """
    创建单个客户接口
    
    Request Body (JSON):
        - customer_name: 客户名称（必填）
        - contact_person: 联系人（可选）
        - contact_phone: 联系电话（可选）
        - contact_address: 联系地址（可选）
        
    Response:
        - success: 是否成功
        - message: 响应消息
        - data: 创建的客户信息
    """
    try:
        data = request.get_json()
        
        if not data or "customer_name" not in data:
            return jsonify({
                "success": False,
                "message": "客户名称不能为空"
            }), 400
        
        service = get_customer_app_service()
        result = service.create(data)
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"创建失败：{str(e)}"
        }), 500


@customers_bp.route("/<int:customer_id>", methods=["GET"])
@swag_from({
    'summary': '获取单个客户',
    'description': '根据 ID 获取客户详细信息',
    'parameters': [
        {
            'name': 'customer_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '客户 ID'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'customer_name': {'type': 'string'},
                            'contact_person': {'type': 'string'},
                            'contact_phone': {'type': 'string'},
                            'contact_address': {'type': 'string'},
                            'created_at': {'type': 'string', 'format': 'date-time'},
                            'updated_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        '404': {
            'description': '客户不存在'
        }
    }
})
def customers_get(customer_id):
    """
    获取单个客户接口
    
    Path Parameters:
        - customer_id: 客户 ID
        
    Response:
        - success: 是否成功
        - data: 客户详细信息
    """
    try:
        service = get_customer_app_service()
        result = service.get_by_id(customer_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@customers_bp.route("/<int:customer_id>", methods=["PUT"])
@swag_from({
    'summary': '更新单个客户',
    'description': '根据 ID 更新客户信息',
    'parameters': [
        {
            'name': 'customer_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '客户 ID'
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'customer_name': {
                        'type': 'string',
                        'description': '客户名称',
                        'example': '七彩乐园'
                    },
                    'contact_person': {
                        'type': 'string',
                        'description': '联系人',
                        'example': '张三'
                    },
                    'contact_phone': {
                        'type': 'string',
                        'description': '联系电话',
                        'example': '13800138000'
                    },
                    'contact_address': {
                        'type': 'string',
                        'description': '联系地址',
                        'example': '某某市某某区某某路 123 号'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '更新成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'customer_name': {'type': 'string'},
                            'contact_person': {'type': 'string'},
                            'contact_phone': {'type': 'string'},
                            'contact_address': {'type': 'string'},
                            'created_at': {'type': 'string', 'format': 'date-time'},
                            'updated_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        '400': {
            'description': '请求参数错误'
        },
        '404': {
            'description': '客户不存在'
        }
    }
})
def customers_update(customer_id):
    """
    更新单个客户接口
    
    Path Parameters:
        - customer_id: 客户 ID
        
    Request Body (JSON):
        - customer_name: 客户名称（可选）
        - contact_person: 联系人（可选）
        - contact_phone: 联系电话（可选）
        - contact_address: 联系地址（可选）
        
    Response:
        - success: 是否成功
        - message: 响应消息
        - data: 更新后的客户信息
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "请求体不能为空"
            }), 400
        
        service = get_customer_app_service()
        result = service.update(customer_id, data)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400 if "不存在" in result.get("message", "") else 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新失败：{str(e)}"
        }), 500


@customers_bp.route("/<int:customer_id>", methods=["DELETE"])
@swag_from({
    'summary': '删除单个客户',
    'description': '根据 ID 删除客户',
    'parameters': [
        {
            'name': 'customer_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '客户 ID'
        }
    ],
    'responses': {
        '200': {
            'description': '删除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'deleted_count': {'type': 'integer'}
                }
            }
        },
        '404': {
            'description': '客户不存在'
        }
    }
})
def customers_delete(customer_id):
    """
    删除单个客户接口

    Path Parameters:
        - customer_id: 客户 ID

    Query Parameters:
        - force: 是否强制删除（可选，忽略关联检查）

    Response:
        - success: 是否成功
        - message: 删除结果消息
        - deleted_count: 删除的记录数
        - has_associations: 是否有关联记录（仅在有关联时返回）
        - association_details: 关联详情（仅在有关联时返回）
    """
    try:
        service = get_customer_app_service()
        force = request.args.get("force", "false").lower() in ("true", "1", "yes")
        result = service.delete(customer_id, force=force)

        if result["success"]:
            return jsonify(result), 200
        else:
            status_code = 409 if result.get("has_associations") else 404
            return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500


@customers_bp.route("/batch-delete", methods=["POST", "DELETE"])
def customers_batch_delete():
    """
    批量删除客户接口

    Request Body (JSON):
        - ids: 客户 ID 数组，例如 [1, 2, 3]
        - force: 是否强制删除（可选，忽略关联检查）

    Response:
        - success: 是否成功
        - message: 删除结果消息
        - deleted_count: 删除的记录数
        - has_associations: 是否有关联记录（仅在有关联时返回）
        - affected_units: 关联详情（仅在有关联时返回）
    """
    try:
        # 支持 POST 和 DELETE 方法
        if request.method == "DELETE":
            ids_str = request.args.get("ids", "")
            ids = [int(id.strip()) for id in ids_str.split(",") if id.strip()]
            force = request.args.get("force", "false").lower() in ("true", "1", "yes")
        else:
            data = request.get_json() or {}
            ids = data.get("ids", [])
            force = data.get("force", False)

        if not ids:
            return jsonify({
                "success": False,
                "message": "ID 列表不能为空"
            }), 400

        service = get_customer_app_service()
        result = service.batch_delete(ids, force=force)

        if result["success"]:
            return jsonify(result), 200
        else:
            status_code = 409 if result.get("has_associations") else 400
            return jsonify(result), status_code

    except ValueError as e:
        return jsonify({
            "success": False,
            "message": f"ID 格式错误：{str(e)}"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500


@customers_bp.route("/list", methods=["GET"])
def customers_list():
    """
    购买单位列表接口
    
    Query Parameters:
        - keyword: 搜索关键词（可选）
        - page: 页码（可选，默认 1）
        - per_page: 每页数量（可选，默认 20）
        
    Response:
        - success: 是否成功
        - data: 购买单位列表
        - total: 总数
        - page: 当前页
        - per_page: 每页数量
    """
    try:
        keyword = request.args.get("keyword")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        result = get_all_customers(keyword=keyword, page=page, per_page=per_page)

        return jsonify(json_safe(result)), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


# ============================================================================
# 辅助函数 - 调用服务层
# ============================================================================

def import_customers_from_excel(file):
    """从 Excel 文件导入客户"""
    try:
        service = get_customer_app_service()
        result = service.import_from_excel(file)
        return True, result, 200
    except Exception as e:
        return False, {"success": False, "message": str(e)}, 500


def export_customers_to_excel(keyword=None, template_id=None):
    """导出客户到 Excel"""
    try:
        service = get_customer_app_service()
        result = service.export_to_excel(keyword=keyword, template_id=template_id)
        return True, result, 200
    except Exception as e:
        return False, {"success": False, "message": str(e)}, 500


def get_all_customers(keyword=None, page=1, per_page=20):
    """获取所有客户"""
    try:
        service = get_customer_app_service()
        result = service.get_all(keyword=keyword, page=page, per_page=per_page)
        return result
    except Exception as e:
        return {"success": False, "message": str(e), "data": [], "total": 0}
