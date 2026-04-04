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

import logging
import os
import time
import uuid
from typing import Any, Dict

from flasgger import swag_from
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

print_bp = Blueprint("print", __name__, url_prefix="/api/print")


_PRINT_CONFIRM_TTL_SECONDS = 300
_print_confirm_cache: Dict[str, Dict[str, Any]] = {}


def _cleanup_print_confirm_cache() -> None:
    now = time.time()
    expired = [
        token
        for token, payload in _print_confirm_cache.items()
        if float(payload.get("expires_at", 0.0)) <= now
    ]
    for token in expired:
        _print_confirm_cache.pop(token, None)


def _create_print_confirm_token(payload: Dict[str, Any]) -> str:
    _cleanup_print_confirm_cache()
    token = uuid.uuid4().hex
    _print_confirm_cache[token] = {
        **payload,
        "expires_at": time.time() + _PRINT_CONFIRM_TTL_SECONDS,
    }
    return token


def _consume_print_confirm_token(token: str) -> Dict[str, Any]:
    _cleanup_print_confirm_cache()
    return _print_confirm_cache.pop(token, {})


def get_printer_service():
    from app.services import get_printer_service as _get
    return _get()


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


@print_bp.route("/printer-selection", methods=["GET"])
def get_printer_selection():
    """获取自定义打印机选择配置"""
    try:
        service = get_printer_service()
        selection = service.get_printer_selection()
        return jsonify({
            "success": True,
            "selection": selection
        })
    except Exception as e:
        logger.error(f"获取打印机选择失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"获取打印机选择失败: {str(e)}"
        }), 500


@print_bp.route("/printer-selection", methods=["PUT"])
def save_printer_selection():
    """保存自定义打印机选择配置"""
    try:
        data = request.json if request.is_json else {}
        document_printer = data.get("document_printer")
        label_printer = data.get("label_printer")

        service = get_printer_service()
        printers_result = service.get_printers()
        printers = printers_result.get("printers", [])
        available_names = {(p.get("name") or "").strip() for p in printers if isinstance(p, dict)}

        def is_valid(name: Any) -> bool:
            if name is None:
                return True
            value = str(name).strip()
            return value == "" or value in available_names

        if not is_valid(document_printer):
            return jsonify({
                "success": False,
                "message": "发货单打印机不在当前可用打印机列表中"
            }), 400
        if not is_valid(label_printer):
            return jsonify({
                "success": False,
                "message": "标签打印机不在当前可用打印机列表中"
            }), 400

        result = service.save_printer_selection(
            document_printer=str(document_printer).strip() if document_printer is not None else None,
            label_printer=str(label_printer).strip() if label_printer is not None else None
        )
        result.update(service.classify_printers(printers))
        return jsonify(result)
    except Exception as e:
        logger.error(f"保存打印机选择失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"保存打印机选择失败: {str(e)}"
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
        require_confirm = bool(data.get("require_confirm", True))
        confirm_token = str(data.get("confirm_token") or "").strip()
        confirm_action = str(data.get("confirm_action") or "").strip().lower()

        try:
            copies = int(copies)
        except Exception:
            copies = 0

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

        # 默认策略：先询问再打印，避免误打印。
        if require_confirm:
            if confirm_action == "cancel":
                if confirm_token:
                    _consume_print_confirm_token(confirm_token)
                return jsonify({
                    "success": True,
                    "status": "print_cancelled",
                    "message": "已取消打印"
                }), 200

            if not confirm_token:
                resolved_printer = printer_name or service.get_label_printer()
                token = _create_print_confirm_token({
                    "file_path": file_path,
                    "printer_name": resolved_printer,
                    "copies": copies,
                })
                return jsonify({
                    "success": True,
                    "status": "print_confirm_required",
                    "require_confirm": True,
                    "confirm_token": token,
                    "confirm_prompt": (
                        f"已准备打印 {copies} 份标签，是否立即打印到【{resolved_printer or '自动选择打印机'}】？"
                    ),
                    "preview": {
                        "file_path": file_path,
                        "label_count": copies,
                        "printer": resolved_printer,
                    },
                    "message": "已生成标签，等待打印确认"
                }), 200

            token_payload = _consume_print_confirm_token(confirm_token)
            if not token_payload:
                return jsonify({
                    "success": False,
                    "status": "print_confirm_required",
                    "error_code": "print_confirm_required",
                    "message": "打印确认已过期或无效，请重新发起打印请求"
                }), 400

            # 使用确认阶段缓存的打印参数，防止二次请求参数漂移。
            file_path = str(token_payload.get("file_path") or file_path)
            copies = int(token_payload.get("copies") or copies)
            printer_name = token_payload.get("printer_name") or printer_name

        result = service.print_label(file_path, printer_name, copies)
        if isinstance(result, dict):
            result.setdefault("status", "printed")
            result.setdefault("require_confirm", False)

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


@print_bp.route("/list_labels", methods=["GET"])
@swag_from({
    'summary': '获取标签列表',
    'description': '获取商标导出目录下的标签文件列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'labels': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'filename': {'type': 'string'},
                                'order_number': {'type': 'string'},
                                'label_number': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def list_labels():
    """
    获取标签列表

    请求参数：
    - limit: 返回数量限制，默认 2（只显示最新 2 个）

    响应：
    {
        "success": True,
        "labels": [
            {"filename": "xxx.png", "order_number": "26-0300001A", "label_number": "1"}
        ]
    }
    """
    try:
        import re

        from app.utils.path_utils import get_resource_path

        labels_dir = get_resource_path("ai_assistant", "商标导出")
        if not os.path.isdir(labels_dir):
            return jsonify({
                "success": True,
                "labels": [],
                "message": "商标导出目录不存在"
            })

        limit = request.args.get('limit', 2, type=int)
        limit = max(1, min(limit, 20))

        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
        labels = []

        for filename in os.listdir(labels_dir):
            ext = os.path.splitext(filename.lower())[1]
            if ext not in image_extensions:
                continue

            file_path = os.path.join(labels_dir, filename)
            if not os.path.isfile(file_path):
                continue

            match = re.match(r"(.+?)_?第？?(\d+)?项？\.png", filename, re.IGNORECASE)
            order_number = match.group(1) if match else os.path.splitext(filename)[0]
            label_number = match.group(2) if match and match.group(2) else "1"

            labels.append({
                "filename": filename,
                "order_number": order_number.strip() if order_number else "",
                "label_number": label_number.strip() if label_number else "1"
            })

        labels.sort(key=lambda x: x.get("filename", ""), reverse=True)
        labels = labels[:limit]

        return jsonify({
            "success": True,
            "labels": labels
        })

    except Exception as e:
        logger.error(f"获取标签列表失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "labels": [],
            "message": str(e)
        }), 500


@print_bp.route("/label/<filename>", methods=["GET"])
def serve_label_image(filename):
    """提供标签图片文件"""
    try:
        from flask import send_from_directory

        from app.utils.path_utils import get_resource_path

        labels_dir = get_resource_path("ai_assistant", "商标导出")
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(labels_dir, safe_filename)

        if not os.path.exists(file_path):
            logger.warning(f"标签文件不存在: {file_path}")
            return jsonify({"success": False, "message": "文件不存在"}), 404

        return send_from_directory(labels_dir, safe_filename, mimetype='image/png')
    except Exception as e:
        logger.error(f"获取标签图片失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500
