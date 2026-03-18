# -*- coding: utf-8 -*-
"""
打印管理路由模块

提供打印功能接口，包括：
- /api/printers: 获取打印机列表
- /api/print/document: 打印文档
- /api/print/label: 打印标签
- /api/print/test: 测试打印机
- /api/print/validate: 验证打印机分离
"""

import os
import logging
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from typing import Dict, Any

logger = logging.getLogger(__name__)

print_bp = Blueprint("print", __name__, url_prefix="/api/print")


def get_printer_service():
    from app.services.printer_service import printer_service
    return printer_service


@print_bp.route("/printers", methods=["GET"])
@swag_from({
    'summary': '获取打印机列表',
    'description': '获取系统中所有可用的打印机',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'printers': {'type': 'array'}
                }
            }
        }
    }
})
def get_printers():
    """
    获取可用打印机列表

    响应：
    {
        "success": True,
        "printers": [...],
        "count": 2
    }
    """
    try:
        service = get_printer_service()
        result = service.get_printers()

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取打印机列表失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"获取打印机列表失败: {str(e)}",
            "printers": []
        }), 500


@print_bp.route("/default", methods=["GET"])
@swag_from({
    'summary': '获取默认打印机',
    'description': '获取系统默认打印机',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'printer': {'type': 'string'}
                }
            }
        }
    }
})
def get_default_printer():
    """
    获取默认打印机

    响应：
    {
        "success": True,
        "printer": "打印机名称"
    }
    """
    try:
        service = get_printer_service()
        result = service.get_default_printer()

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取默认打印机失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@print_bp.route("/document", methods=["POST"])
@swag_from({
    'summary': '打印文档',
    'description': '打印文档文件',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': '文件路径'},
                    'printer': {'type': 'string', 'description': '打印机名称（可选）'}
                },
                'required': ['file_path']
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
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def print_document():
    """
    打印文档

    请求：
    {
        "file_path": "文件路径",
        "printer_name": "打印机名称（可选）",
        "use_automation": false
    }

    响应：
    {
        "success": True,
        "message": "打印成功",
        "printer": "打印机名称"
    }
    """
    try:
        data = request.json if request.is_json else {}

        file_path = data.get("file_path", "")
        printer_name = data.get("printer_name")
        use_automation = data.get("use_automation", False)

        if not file_path:
            return jsonify({
                "success": False,
                "message": "文件路径不能为空"
            }), 400

        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "message": f"文件不存在: {file_path}"
            }), 400

        service = get_printer_service()
        result = service.print_document(file_path, printer_name, use_automation)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"打印文档失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"打印失败: {str(e)}"
        }), 500


@print_bp.route("/label", methods=["POST"])
@swag_from({
    'summary': '打印标签',
    'description': '打印标签',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'content': {'type': 'string', 'description': '标签内容'},
                    'printer': {'type': 'string', 'description': '打印机名称（可选）'}
                },
                'required': ['content']
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
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def print_label():
    """
    打印标签

    请求：
    {
        "file_path": "标签文件路径",
        "printer_name": "打印机名称（可选）",
        "copies": 1
    }

    响应：
    {
        "success": True,
        "message": "标签打印完成: 1/1 成功",
        "printer": "打印机名称",
        "copies": 1
    }
    """
    try:
        data = request.json if request.is_json else {}

        file_path = data.get("file_path", "")
        printer_name = data.get("printer_name")
        copies = data.get("copies", 1)

        if not file_path:
            return jsonify({
                "success": False,
                "message": "文件路径不能为空"
            }), 400

        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "message": f"文件不存在: {file_path}"
            }), 400

        if copies < 1 or copies > 100:
            return jsonify({
                "success": False,
                "message": "打印份数必须在1-100之间"
            }), 400

        service = get_printer_service()
        result = service.print_label(file_path, printer_name, copies)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"打印标签失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"打印标签失败: {str(e)}"
        }), 500


@print_bp.route("/test", methods=["POST"])
@swag_from({
    'summary': '测试打印机',
    'description': '测试打印机是否正常工作',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'printer': {'type': 'string', 'description': '打印机名称'}
                },
                'required': ['printer']
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
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def test_printer():
    """
    测试打印机

    请求：
    {
        "printer_name": "打印机名称"
    }

    响应：
    {
        "success": True,
        "available": True,
        "printer": "打印机名称",
        "status": "就绪"
    }
    """
    try:
        data = request.json if request.is_json else {}
        printer_name = data.get("printer_name", "")

        if not printer_name:
            return jsonify({
                "success": False,
                "message": "打印机名称不能为空"
            }), 400

        service = get_printer_service()
        result = service.test_printer(printer_name)

        return jsonify(result)

    except Exception as e:
        logger.error(f"测试打印机失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@print_bp.route("/validate", methods=["GET"])
@swag_from({
    'summary': '验证打印机分离',
    'description': '验证文档打印机和标签打印机是否正确分离',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'document_printer': {'type': 'string'},
                    'label_printer': {'type': 'string'},
                    'is_valid': {'type': 'boolean'}
                }
            }
        }
    }
})
def validate_printer_separation():
    """
    验证打印机分离配置

    响应：
    {
        "valid": True,
        "doc_printer": "发货单打印机",
        "label_printer": "标签打印机"
    }
    """
    try:
        service = get_printer_service()
        result = service.validate_printer_separation()

        return jsonify({
            "success": True,
            **result
        })

    except Exception as e:
        logger.error(f"验证打印机分离失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "valid": False,
            "error": str(e)
        }), 500


@print_bp.route("/document-printer", methods=["GET"])
@swag_from({
    'summary': '获取发货单打印机',
    'description': '获取发货单使用的打印机',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'printer': {'type': 'string'}
                }
            }
        }
    }
})
def get_document_printer():
    """
    获取发货单打印机

    响应：
    {
        "success": True,
        "printer": "发货单打印机名称"
    }
    """
    try:
        service = get_printer_service()
        printer = service.get_document_printer()

        if printer:
            return jsonify({
                "success": True,
                "printer": printer
            })
        else:
            return jsonify({
                "success": False,
                "message": "未找到发货单打印机"
            })

    except Exception as e:
        logger.error(f"获取发货单打印机失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@print_bp.route("/label-printer", methods=["GET"])
@swag_from({
    'summary': '获取标签打印机',
    'description': '获取标签打印机',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'printer': {'type': 'string'}
                }
            }
        }
    }
})
def get_label_printer():
    """
    获取标签打印机

    响应：
    {
        "success": True,
        "printer": "标签打印机名称"
    }
    """
    try:
        service = get_printer_service()
        printer = service.get_label_printer()

        if printer:
            return jsonify({
                "success": True,
                "printer": printer
            })
        else:
            return jsonify({
                "success": False,
                "message": "未找到标签打印机"
            })

    except Exception as e:
        logger.error(f"获取标签打印机失败: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@print_bp.route("/test", methods=["GET"])
@swag_from({
    'summary': '测试打印服务',
    'description': '测试打印服务是否正常运行',
    'responses': {
        '200': {
            'description': '成功响应',
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
def test():
    """
    测试接口

    响应：
    {
        "success": True,
        "message": "打印服务运行正常"
    }
    """
    return jsonify({
        "success": True,
        "message": "打印服务运行正常",
    })
