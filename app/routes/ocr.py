# -*- coding: utf-8 -*-
"""
OCR路由模块

提供图像文字识别、结构化数据提取等 HTTP 接口。
"""

import logging
import os
from functools import lru_cache
from typing import Any, Dict

from flasgger import swag_from
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ocr_bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")


@lru_cache(maxsize=1)
def get_ocr_service():
    from app.services import get_ocr_service as _get
    return _get()


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@ocr_bp.route("/recognize", methods=["POST"])
@swag_from({
    'summary': 'OCR 文字识别',
    'description': '识别图像中的文字',
    'parameters': [
        {
            'name': 'image',
            'in': 'formData',
            'type': 'file',
            'required': False,
            'description': '图像文件'
        },
        {
            'name': 'file_path',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': '文件路径'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'text': {'type': 'string'}
                }
            }
        }
    }
})
def ocr_recognize():
    """
    识别图像中的文字

    Request:
        - image: 图像文件
        - file_path: 或直接提供文件路径

    Response:
        - success: 是否成功
        - text: 识别出的文字
    """
    try:
        file_path = request.form.get("file_path")
        image_file = request.files.get("image")

        if image_file:
            filename = secure_filename(image_file.filename)
            from app.utils.path_utils import get_upload_dir

            upload_dir = os.path.join(get_upload_dir(), "ocr")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            image_file.save(file_path)

        if not file_path:
            return jsonify({
                "success": False,
                "message": "请提供图像文件或文件路径"
            }), 400

        service = get_ocr_service()
        result = service.recognize_file(file_path)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.exception(f"OCR识别失败: {e}")
        return jsonify({
            "success": False,
            "message": f"识别失败: {str(e)}"
        }), 500


@ocr_bp.route("/extract", methods=["POST"])
@swag_from({
    'summary': '提取结构化数据',
    'description': '从OCR文本中提取结构化数据',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'OCR识别出的文字'}
                },
                'required': ['text']
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
                    'data': {'type': 'object'}
                }
            }
        }
    }
})
def ocr_extract():
    """
    从OCR文本中提取结构化数据

    Request:
        - text: OCR识别出的文字

    Response:
        - success: 是否成功
        - data: 结构化数据
    """
    try:
        data = request.get_json() or {}
        text = data.get("text", "")

        if not text:
            return jsonify({
                "success": False,
                "message": "文本不能为空"
            }), 400

        service = get_ocr_service()
        result = service.extract_structured_data(text)

        return jsonify({
            "success": True,
            "data": result
        }), 200

    except Exception as e:
        logger.exception(f"提取结构化数据失败: {e}")
        return jsonify({
            "success": False,
            "message": f"提取失败: {str(e)}"
        }), 500


@ocr_bp.route("/analyze", methods=["POST"])
@swag_from({
    'summary': '分析OCR文本',
    'description': '分析OCR文本内容',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'OCR识别出的文字'}
                },
                'required': ['text']
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
                    'analysis': {'type': 'object'}
                }
            }
        }
    }
})
def ocr_analyze():
    """
    分析OCR文本内容

    Request:
        - text: OCR识别出的文字

    Response:
        - success: 是否成功
        - data: 分析结果
    """
    try:
        data = request.get_json() or {}
        text = data.get("text", "")

        if not text:
            return jsonify({
                "success": False,
                "message": "文本不能为空"
            }), 400

        service = get_ocr_service()
        result = service.analyze_text(text)

        return jsonify({
            "success": True,
            "data": result
        }), 200

    except Exception as e:
        logger.exception(f"分析文本失败: {e}")
        return jsonify({
            "success": False,
            "message": f"分析失败: {str(e)}"
        }), 500


@ocr_bp.route("/recognize-and-extract", methods=["POST"])
@swag_from({
    'summary': '识别并提取',
    'description': '一站式：识别图像并提取结构化数据',
    'parameters': [
        {
            'name': 'image',
            'in': 'formData',
            'type': 'file',
            'required': False,
            'description': '图像文件'
        },
        {
            'name': 'file_path',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': '文件路径'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'text': {'type': 'string'},
                    'data': {'type': 'object'}
                }
            }
        }
    }
})
def ocr_recognize_and_extract():
    """
    一站式：识别图像并提取结构化数据

    Request:
        - image: 图像文件
        - file_path: 或直接提供文件路径

    Response:
        - success: 是否成功
        - text: 识别出的文字
        - data: 结构化数据
    """
    try:
        file_path = request.form.get("file_path")
        image_file = request.files.get("image")

        if image_file:
            filename = secure_filename(image_file.filename)
            from app.utils.path_utils import get_upload_dir

            upload_dir = os.path.join(get_upload_dir(), "ocr")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            image_file.save(file_path)

        if not file_path:
            return jsonify({
                "success": False,
                "message": "请提供图像文件或文件路径"
            }), 400

        service = get_ocr_service()

        recognize_result = service.recognize_file(file_path)
        if not recognize_result.get("success"):
            return jsonify(recognize_result), 400

        text = recognize_result.get("text", "")
        structured_data = service.extract_structured_data(text)
        analysis = service.analyze_text(text)

        return jsonify({
            "success": True,
            "message": "识别和提取成功",
            "text": text,
            "data": structured_data,
            "analysis": analysis
        }), 200

    except Exception as e:
        logger.exception(f"OCR识别和提取失败: {e}")
        return jsonify({
            "success": False,
            "message": f"处理失败: {str(e)}"
        }), 500


@ocr_bp.route("/test", methods=["GET"])
@swag_from({
    'summary': '测试OCR服务',
    'description': '测试OCR服务是否正常运行',
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
def ocr_test():
    """测试接口"""
    try:
        svc = get_ocr_service()
        backend = svc.get_active_ocr_backend()
    except Exception:
        backend = "unknown"
    return jsonify({
        "success": True,
        "message": "OCR服务运行正常",
        "active_backend": backend,
    }), 200
