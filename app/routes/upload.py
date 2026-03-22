# -*- coding: utf-8 -*-
"""
文件上传 API 路由
提供 /api/upload/* 路径的 API 端点
"""

import logging
import os
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')
CORS(upload_bp)

# 配置
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# 上传目录
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'temp')


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_upload_folder():
    """确保上传目录存在"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@upload_bp.route('/temp', methods=['POST'])
def upload_temp():
    """
    上传临时文件（图片）
    
    用于标签模板生成等功能，上传的图片会在 24 小时后自动清理
    
    Returns:
        {
            "success": true,
            "file_path": "uploads/temp/xxx.png",
            "filename": "original_name.png",
            "url": "/uploads/temp/xxx.png"
        }
    """
    try:
        # 确保上传目录存在
        ensure_upload_folder()
        
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "没有上传文件"
            }), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "文件名为空"
            }), 400
        
        # 验证文件类型
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": f"不支持的文件类型，仅支持：{', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        if not original_filename:
            original_filename = "uploaded_file"
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'png'
        new_filename = f"{timestamp}_{unique_id}.{ext}"
        
        # 保存文件
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(file_path)
        
        # 验证文件确实被保存
        if not os.path.exists(file_path):
            logger.error(f"文件保存失败：{file_path}")
            return jsonify({
                "success": False,
                "message": "文件保存失败"
            }), 500
        
        # 返回相对路径（相对于项目根目录）
        relative_path = os.path.join('uploads', 'temp', new_filename)
        
        logger.info(f"文件上传成功：{relative_path}")
        
        return jsonify({
            "success": True,
            "file_path": relative_path,
            "filename": original_filename,
            "url": f"/{relative_path.replace(os.sep, '/')}",
            "size": os.path.getsize(file_path)
        })
        
    except Exception as e:
        logger.error(f"文件上传失败：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"上传失败：{str(e)}"
        }), 500


@upload_bp.route('/temp/<filename>', methods=['DELETE'])
def delete_temp_file(filename):
    """
    删除临时文件
    
    Args:
        filename: 文件名
    
    Returns:
        {
            "success": true,
            "message": "文件已删除"
        }
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "message": "文件不存在"
            }), 404
        
        os.remove(file_path)
        
        return jsonify({
            "success": True,
            "message": "文件已删除"
        })
        
    except Exception as e:
        logger.error(f"删除文件失败：{e}")
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500


@upload_bp.route('/config', methods=['GET'])
def get_upload_config():
    """
    获取上传配置信息
    
    Returns:
        {
            "success": true,
            "config": {
                "max_size": "16MB",
                "allowed_extensions": ["png", "jpg", "jpeg", "gif", "webp"]
            }
        }
    """
    return jsonify({
        "success": True,
        "config": {
            "max_size": "16MB",
            "max_size_bytes": MAX_CONTENT_LENGTH,
            "allowed_extensions": list(ALLOWED_EXTENSIONS)
        }
    })
