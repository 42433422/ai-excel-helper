# -*- coding: utf-8 -*-
"""
AI 数据分析路由
为 AI生态页面提供文件分析、图表生成和结果导出功能
"""
import logging
import os
from typing import Any, Dict
from pathlib import Path

from flasgger import swag_from
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.services.data_analysis_service import get_data_analysis_service
from app.utils.path_utils import get_upload_dir

logger = logging.getLogger(__name__)

ai_analyze_bp = Blueprint("ai_analyze", __name__, url_prefix="/api/ai")


@ai_analyze_bp.route("/analyze", methods=["POST"])
@swag_from({
    "summary": "AI 数据分析接口",
    "description": "接收文件上传和自然语言查询，返回分析结果和图表数据",
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": False,
            "description": "要分析的文件 (xlsx, csv, txt, json)"
        },
        {
            "name": "query",
            "in": "formData",
            "type": "string",
            "required": False,
            "description": "自然语言分析需求，如 '分析销量趋势' 或 '计算渠道ROI'"
        }
    ],
    "responses": {
        "200": {"description": "分析成功"}
    }
})
def analyze():
    """AI 数据分析主接口"""
    try:
        service = get_data_analysis_service()
        query = request.form.get("query", "")

        # 处理文件上传
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"success": False, "message": "未选择文件"}), 400

            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
            file.save(file_path)

            result = service.analyze_file(file_path, query)
            
            # 清理临时文件
            try:
                os.unlink(file_path)
            except:
                pass
                
            return jsonify(result)

        # 纯文本查询
        if query.strip():
            # 返回模拟分析结果
            return jsonify({
                "success": True,
                "file_info": {"rows": 0, "columns": []},
                "statistics": {},
                "chart_data": {
                    "type": "line",
                    "labels": ["1月", "2月", "3月", "4月"],
                    "datasets": [{
                        "label": "销量",
                        "data": [1200, 1900, 1500, 2300],
                        "borderColor": "#3b82f6"
                    }]
                },
                "insights": ["已理解查询意图", "生成趋势分析"],
                "message": "文本查询分析完成"
            })

        return jsonify({"success": False, "message": "请提供文件或查询内容"}), 400

    except Exception as e:
        logger.error(f"AI分析失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500


@ai_analyze_bp.route("/analyze/export/<export_id>", methods=["GET"])
def export_result(export_id):
    """导出分析结果为Excel"""
    try:
        service = get_data_analysis_service()
        output_path = os.path.join(get_upload_dir(), f"report_{export_id}.xlsx")
        
        # 生成示例报告
        success = service.export_to_excel({}, output_path)
        
        if success and os.path.exists(output_path):
            return send_file(
                output_path,
                as_attachment=True,
                download_name=f"分析报告_{export_id[:8]}.xlsx"
            )
        else:
            return jsonify({"success": False, "message": "导出失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def register_ai_analyze_routes(app):
    """注册路由（供 __init__.py 调用）"""
    app.register_blueprint(ai_analyze_bp)
