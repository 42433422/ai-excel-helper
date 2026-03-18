"""
原材料仓库路由

提供原材料管理相关 HTTP 接口。
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from
import logging

from app.services.materials_service import MaterialsService

logger = logging.getLogger(__name__)
materials_bp = Blueprint("materials", __name__)


@materials_bp.route("/api/materials", methods=["POST"])
@swag_from({
    'summary': '添加原材料',
    'description': '添加一个新的原材料记录',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['material_code', 'name'],
                'properties': {
                    'material_code': {'type': 'string', 'description': '原材料编码'},
                    'name': {'type': 'string', 'description': '原材料名称'},
                    'category': {'type': 'string', 'description': '分类'},
                    'specification': {'type': 'string', 'description': '规格型号'},
                    'unit': {'type': 'string', 'description': '单位', 'default': '个'},
                    'quantity': {'type': 'number', 'description': '数量', 'default': 0},
                    'unit_price': {'type': 'number', 'description': '单价', 'default': 0},
                    'supplier': {'type': 'string', 'description': '供应商'},
                    'warehouse_location': {'type': 'string', 'description': '仓库位置'},
                    'min_stock': {'type': 'number', 'description': '最低库存', 'default': 0},
                    'max_stock': {'type': 'number', 'description': '最高库存', 'default': 0},
                    'description': {'type': 'string', 'description': '描述信息'}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': '创建成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'}
                }
            }
        },
        '400': {
            'description': '请求参数错误'
        }
    }
})
def add_material():
    """添加原材料"""
    try:
        data = request.get_json() or {}
        
        if not data.get('material_code') or not data.get('name'):
            return jsonify({
                "success": False,
                "message": "原材料编码和名称不能为空"
            }), 400
        
        service = MaterialsService()
        result = service.create_material(
            material_code=data.get('material_code'),
            name=data.get('name'),
            category=data.get('category'),
            specification=data.get('specification'),
            unit=data.get('unit', '个'),
            quantity=data.get('quantity', 0),
            unit_price=data.get('unit_price', 0),
            supplier=data.get('supplier'),
            warehouse_location=data.get('warehouse_location'),
            min_stock=data.get('min_stock', 0),
            max_stock=data.get('max_stock', 0),
            description=data.get('description')
        )
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"添加原材料失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@materials_bp.route("/api/materials", methods=["GET"])
@swag_from({
    'summary': '获取原材料列表',
    'description': '获取原材料列表，支持搜索和分页',
    'parameters': [
        {
            'name': 'search',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '搜索关键词（名称/编码/供应商）'
        },
        {
            'name': 'category',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '分类筛选'
        },
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '页码，默认 1'
        },
        {
            'name': 'per_page',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'description': '每页数量，默认 20'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'array'},
                    'total': {'type': 'integer'},
                    'page': {'type': 'integer'},
                    'per_page': {'type': 'integer'}
                }
            }
        }
    }
})
def get_materials():
    """获取原材料列表"""
    try:
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        service = MaterialsService()
        result = service.get_all_materials(
            search=search,
            category=category if category else None,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"获取原材料列表失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@materials_bp.route("/api/materials/<int:material_id>", methods=["PUT"])
@swag_from({
    'summary': '更新原材料',
    'description': '根据 ID 更新原材料信息',
    'parameters': [
        {
            'name': 'material_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '原材料 ID'
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'material_code': {'type': 'string', 'description': '原材料编码'},
                    'name': {'type': 'string', 'description': '原材料名称'},
                    'category': {'type': 'string', 'description': '分类'},
                    'specification': {'type': 'string', 'description': '规格型号'},
                    'unit': {'type': 'string', 'description': '单位'},
                    'quantity': {'type': 'number', 'description': '数量'},
                    'unit_price': {'type': 'number', 'description': '单价'},
                    'supplier': {'type': 'string', 'description': '供应商'},
                    'warehouse_location': {'type': 'string', 'description': '仓库位置'},
                    'min_stock': {'type': 'number', 'description': '最低库存'},
                    'max_stock': {'type': 'number', 'description': '最高库存'},
                    'description': {'type': 'string', 'description': '描述信息'}
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
                    'data': {'type': 'object'}
                }
            }
        },
        '400': {
            'description': '请求参数错误'
        },
        '404': {
            'description': '原材料不存在'
        }
    }
})
def update_material(material_id):
    """更新原材料"""
    try:
        data = request.get_json() or {}
        
        if not data:
            return jsonify({
                "success": False,
                "message": "请求体不能为空"
            }), 400
        
        service = MaterialsService()
        result = service.update_material(material_id, **data)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400 if "不存在" in result.get("message", "") else 400
            
    except Exception as e:
        logger.error(f"更新原材料失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@materials_bp.route("/api/materials/<int:material_id>", methods=["DELETE"])
@swag_from({
    'summary': '删除原材料',
    'description': '根据 ID 删除原材料（软删除）',
    'parameters': [
        {
            'name': 'material_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '原材料 ID'
        }
    ],
    'responses': {
        '200': {
            'description': '删除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '404': {
            'description': '原材料不存在'
        }
    }
})
def delete_material(material_id):
    """删除原材料"""
    try:
        service = MaterialsService()
        result = service.delete_material(material_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"删除原材料失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@materials_bp.route("/api/materials/batch-delete", methods=["POST"])
@swag_from({
    'summary': '批量删除原材料',
    'description': '批量删除原材料（软删除）',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'ids': {
                        'type': 'array',
                        'description': '原材料 ID 列表',
                        'items': {'type': 'integer'}
                    }
                },
                'required': ['ids']
            }
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
        '400': {
            'description': '请求参数错误'
        }
    }
})
def batch_delete_materials():
    """批量删除原材料"""
    try:
        data = request.get_json() or {}
        
        if not data or 'ids' not in data:
            return jsonify({
                "success": False,
                "message": "请求体中必须包含 ids 字段"
            }), 400
        
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({
                "success": False,
                "message": "ID 列表不能为空"
            }), 400
        
        service = MaterialsService()
        result = service.batch_delete_materials(ids)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"批量删除原材料失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@materials_bp.route("/api/materials/low-stock", methods=["GET"])
@swag_from({
    'summary': '获取低库存原材料',
    'description': '获取低库存原材料列表，用于库存预警',
    'parameters': [
        {
            'name': 'threshold',
            'in': 'query',
            'type': 'number',
            'required': False,
            'description': '库存阈值（不传则使用 min_stock 判断）'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'array'},
                    'count': {'type': 'integer'}
                }
            }
        }
    }
})
def get_low_stock_materials():
    """获取低库存原材料"""
    try:
        threshold = request.args.get('threshold', None, type=float)
        
        service = MaterialsService()
        result = service.get_low_stock_materials(threshold=threshold)
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"获取低库存原材料失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500
