"""
产品库路由蓝图

提供产品库相关 HTTP 接口。
"""

from flask import Blueprint, request, jsonify, send_file
from flasgger import swag_from
import os

from app.services.products_service import ProductsService

products_bp = Blueprint("products", __name__)


@products_bp.route("/", methods=["GET"])
@swag_from({
    'summary': '获取产品列表',
    'description': '获取产品列表，支持分页和关键词搜索',
    'parameters': [
        {
            'name': 'unit',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '单位名称（可选）'
        },
        {
            'name': 'keyword',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '搜索关键词（可选）'
        },
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '页码（默认 1）',
            'default': 1
        },
        {
            'name': 'per_page',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '每页数量（默认 20）',
            'default': 20
        }
    ],
    'responses': {
        '200': {
            'description': '成功获取产品列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'array', 'items': {'type': 'object'}},
                    'total': {'type': 'integer'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def products_list():
    """
    获取产品列表
    
    Query Parameters:
        - unit: 单位名称（可选）
        - keyword: 搜索关键词（可选）
        - page: 页码（可选，默认 1）
        - per_page: 每页数量（可选，默认 20）
        
    Response:
        - success: 是否成功
        - data: 产品列表
        - total: 总数
    """
    try:
        unit_name = request.args.get("unit")
        keyword = request.args.get("keyword")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        service = ProductsService()
        result = service.get_products(
            unit_name=unit_name,
            keyword=keyword,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@products_bp.route("/list", methods=["GET"])
def products_list_legacy():
    """兼容旧版 /list 路由"""
    return products_list()


@products_bp.route("/<int:product_id>", methods=["GET"])
@swag_from({
    'summary': '获取单个产品详情',
    'description': '根据产品 ID 获取产品的详细信息',
    'parameters': [
        {
            'name': 'product_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '产品 ID'
        }
    ],
    'responses': {
        '200': {
            'description': '成功获取产品详情',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'name': {'type': 'string'},
                            'model_number': {'type': 'string'},
                            'specification': {'type': 'string'},
                            'price': {'type': 'number'},
                            'quantity': {'type': 'integer'},
                            'description': {'type': 'string'},
                            'category': {'type': 'string'},
                            'brand': {'type': 'string'},
                            'unit': {'type': 'string'},
                            'is_active': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        '404': {
            'description': '产品不存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_product(product_id):
    """
    获取单个产品详情
    
    Path Parameters:
        - product_id: 产品 ID
        
    Response:
        - success: 是否成功
        - data: 产品详细信息
    """
    try:
        service = ProductsService()
        result = service.get_product(product_id)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@products_bp.route("/add", methods=["POST"])
@swag_from({
    'summary': '添加产品',
    'description': '添加一个新的产品到产品库',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['unit_name', 'product_name', 'price'],
                'properties': {
                    'unit_name': {
                        'type': 'string',
                        'description': '单位名称'
                    },
                    'product_name': {
                        'type': 'string',
                        'description': '产品名称'
                    },
                    'price': {
                        'type': 'number',
                        'description': '价格'
                    },
                    'description': {
                        'type': 'string',
                        'description': '产品描述（可选）'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '产品添加成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'product_id': {'type': 'integer'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def products_add():
    """
    添加产品
    
    Request Body:
        - unit_name: 单位名称
        - product_name: 产品名称
        - price: 价格
        - description: 描述（可选）
        
    Response:
        - success: 是否成功
        - message: 响应消息
        - product_id: 产品 ID
    """
    try:
        data = request.get_json() or {}
        
        service = ProductsService()
        result = service.create_product(data)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"添加失败：{str(e)}"
        }), 500


@products_bp.route("/update", methods=["POST"])
@swag_from({
    'summary': '更新产品',
    'description': '根据产品ID更新产品信息',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['id'],
                'properties': {
                    'id': {
                        'type': 'integer',
                        'description': '产品ID'
                    },
                    'product_name': {
                        'type': 'string',
                        'description': '产品名称'
                    },
                    'price': {
                        'type': 'number',
                        'description': '价格'
                    },
                    'description': {
                        'type': 'string',
                        'description': '产品描述'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '产品更新成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def products_update():
    """
    更新产品
    
    Request Body:
        - id: 产品 ID
        - product_name: 产品名称
        - price: 价格
        - description: 描述
        
    Response:
        - success: 是否成功
        - message: 响应消息
    """
    try:
        data = request.get_json() or {}
        product_id = data.get("id")
        
        if not product_id:
            return jsonify({
                "success": False,
                "message": "产品 ID 不能为空"
            }), 400
        
        service = ProductsService()
        result = service.update_product(product_id, data)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新失败：{str(e)}"
        }), 500


@products_bp.route("/delete", methods=["POST"])
@swag_from({
    'summary': '删除产品',
    'description': '根据产品 ID 删除产品',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['id'],
                'properties': {
                    'id': {
                        'type': 'integer',
                        'description': '产品 ID'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '产品删除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def products_delete():
    """
    删除产品
    
    Request Body:
        - id: 产品 ID
        
    Response:
        - success: 是否成功
        - message: 响应消息
    """
    try:
        data = request.get_json() or {}
        product_id = data.get("id")
        
        if not product_id:
            return jsonify({
                "success": False,
                "message": "产品 ID 不能为空"
            }), 400
        
        service = ProductsService()
        result = service.delete_product(product_id)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500


@products_bp.route("/<int:product_id>", methods=["DELETE"])
def delete_product_by_id(product_id):
    """
    删除单个产品（通过 URL 参数）
    
    Path Parameters:
        - product_id: 产品 ID
        
    Request Body (可选):
        - purchase_unit: 单位名称（用于验证）
        
    Response:
        - success: 是否成功
        - message: 响应消息
    """
    try:
        # 可选的请求体参数
        data = request.get_json(silent=True) or {}
        purchase_unit = data.get("purchase_unit")
        
        service = ProductsService()
        
        # 如果提供了单位名称，可以添加验证逻辑
        if purchase_unit:
            # 这里可以添加验证产品是否属于该单位的逻辑
            pass
        
        result = service.delete_product(product_id)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500


@products_bp.route("/export.xlsx", methods=["GET"])
@swag_from({
    'summary': '导出产品',
    'description': '导出产品列表为 Excel 文件',
    'parameters': [
        {
            'name': 'unit',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '单位名称（可选）'
        },
        {
            'name': 'keyword',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '搜索关键词（可选）'
        }
    ],
    'responses': {
        '200': {
            'description': '导出成功，返回 Excel 文件',
            'schema': {
                'type': 'file'
            }
        },
        '400': {
            'description': '导出失败',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def export_products():
    """
    导出产品为 Excel 文件
    
    Query Parameters:
        - unit: 单位名称（可选）
        - keyword: 搜索关键词（可选）
        
    Response:
        Excel 文件下载
    """
    try:
        unit_name = request.args.get("unit")
        keyword = request.args.get("keyword")
        
        service = ProductsService()
        result = service.export_to_excel(unit_name=unit_name, keyword=keyword)
        
        if not result.get("success"):
            return jsonify(result), 400
        
        file_path = result.get("file_path")
        filename = result.get("filename")
        
        if file_path and os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            return jsonify({
                "success": False,
                "message": "导出文件不存在"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"导出失败：{str(e)}"
        }), 500


@products_bp.route("/product_names", methods=["GET"])
@swag_from({
    'summary': '获取产品名称列表',
    'description': '获取所有产品名称的列表，支持去重',
    'parameters': [],
    'responses': {
        '200': {
            'description': '成功获取产品名称列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'array', 'items': {'type': 'string'}},
                    'count': {'type': 'integer'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_product_names():
    """
    获取产品名称列表
    
    Response:
        - success: 是否成功
        - data: 产品名称列表
        - count: 数量
    """
    try:
        service = ProductsService()
        result = service.get_product_names()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@products_bp.route("/product_names/search", methods=["GET"])
@swag_from({
    'summary': '搜索产品名称',
    'description': '根据关键词搜索产品名称，支持模糊匹配',
    'parameters': [
        {
            'name': 'keyword',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '搜索关键词',
            'default': ''
        }
    ],
    'responses': {
        '200': {
            'description': '成功搜索产品名称',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'array', 'items': {'type': 'string'}},
                    'count': {'type': 'integer'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def search_product_names():
    """
    搜索产品名称
    
    Query Parameters:
        - keyword: 搜索关键词（可选）
        
    Response:
        - success: 是否成功
        - data: 产品名称列表
        - count: 数量
    """
    try:
        keyword = request.args.get('keyword', '')
        service = ProductsService()
        result = service.get_product_names(keyword=keyword)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@products_bp.route("/search", methods=["GET"])
@swag_from({
    'summary': '搜索产品',
    'description': '根据关键词搜索产品',
    'parameters': [
        {
            'name': 'keyword',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '搜索关键词'
        }
    ],
    'responses': {
        '200': {
            'description': '成功搜索产品',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'array', 'items': {'type': 'object'}},
                    'total': {'type': 'integer'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def search_products():
    """搜索产品"""
    try:
        keyword = request.args.get('keyword', '')
        service = ProductsService()
        result = service.get_products(keyword=keyword)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@products_bp.route("/batch", methods=["POST"])
@swag_from({
    'summary': '批量添加产品',
    'description': '批量添加多个产品到产品库',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['products'],
                'properties': {
                    'products': {
                        'type': 'array',
                        'description': '产品列表',
                        'items': {
                            'type': 'object',
                            'required': ['product_name', 'price'],
                            'properties': {
                                'unit_name': {'type': 'string', 'description': '单位名称'},
                                'product_name': {'type': 'string', 'description': '产品名称'},
                                'price': {'type': 'number', 'description': '价格'},
                                'description': {'type': 'string', 'description': '产品描述（可选）'},
                                'model_number': {'type': 'string', 'description': '产品编码'},
                                'specification': {'type': 'string', 'description': '规格型号'},
                                'quantity': {'type': 'integer', 'description': '数量'},
                                'category': {'type': 'string', 'description': '类别'},
                                'brand': {'type': 'string', 'description': '品牌'},
                                'unit': {'type': 'string', 'description': '单位', 'default': '个'},
                                'is_active': {'type': 'integer', 'description': '是否启用', 'default': 1}
                            }
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '批量添加成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'success_count': {'type': 'integer', 'description': '成功添加数量'},
                    'failed_count': {'type': 'integer', 'description': '失败数量'},
                    'product_ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': '成功添加的产品 ID 列表'},
                    'failed_products': {
                        'type': 'array',
                        'description': '失败的产品信息',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'index': {'type': 'integer', 'description': '产品索引'},
                                'reason': {'type': 'string', 'description': '失败原因'}
                            }
                        }
                    }
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def batch_add_products():
    """
    批量添加产品
    
    Request Body:
        - products: 产品列表，每个产品包含：
            - product_name: 产品名称（必填）
            - price: 价格（必填）
            - description: 描述（可选）
            - model_number: 产品编码（可选）
            - specification: 规格型号（可选）
            - quantity: 数量（可选）
            - category: 类别（可选）
            - brand: 品牌（可选）
            - unit: 单位（可选，默认"个"）
            - is_active: 是否启用（可选，默认 1）
            
    Response:
        - success: 是否成功
        - message: 响应消息
        - success_count: 成功添加数量
        - failed_count: 失败数量
        - product_ids: 成功添加的产品 ID 列表
        - failed_products: 失败的产品信息（如果有）
    """
    try:
        data = request.get_json() or {}
        products = data.get('products', [])
        
        if not products:
            return jsonify({
                "success": False,
                "message": "产品列表不能为空"
            }), 400
        
        service = ProductsService()
        result = service.batch_add_products(products)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"批量添加失败：{str(e)}"
        }), 500


@products_bp.route("/batch-delete", methods=["POST"])
@swag_from({
    'summary': '批量删除产品',
    'description': '根据产品ID列表批量删除产品',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['ids'],
                'properties': {
                    'ids': {
                        'type': 'array',
                        'description': '产品ID列表',
                        'items': {
                            'type': 'integer',
                            'description': '产品ID'
                        }
                    },
                    'product_ids': {
                        'type': 'array',
                        'description': '产品ID列表（兼容旧版）',
                        'items': {
                            'type': 'integer',
                            'description': '产品ID'
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '批量删除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def batch_delete_products():
    """批量删除产品"""
    try:
        data = request.get_json() or {}
        # 兼容两种字段名：ids 和 product_ids
        ids = data.get('ids') or data.get('product_ids', [])
        
        if not ids:
            return jsonify({
                "success": False,
                "message": "产品 ID 列表不能为空"
            }), 400
        
        service = ProductsService()
        result = service.batch_delete_products(ids)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"批量删除失败：{str(e)}"
        }), 500
