# -*- coding: utf-8 -*-
"""
Excel 向量化路由模块

提供 Excel 语义索引能力：
- /api/excel/vector/ingest: 上传并建立索引
- /api/excel/vector/query: 语义检索
- /api/excel/vector/indexes: 索引列表
"""

import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.application import (
    get_excel_vector_ingest_app_service,
    get_excel_vector_search_app_service,
)
from app.utils.path_utils import get_upload_dir

logger = logging.getLogger(__name__)

excel_vector_bp = Blueprint("excel_vector", __name__, url_prefix="/api/excel/vector")


@excel_vector_bp.route("/ingest", methods=["POST"])
def ingest_excel_vector():
    """上传 Excel 并构建向量索引。"""
    try:
        ingest_service = get_excel_vector_ingest_app_service()

        payload = request.get_json(silent=True) or {}
        if "excel_file" in request.files:
            upload = request.files["excel_file"]
            if not upload or not upload.filename:
                return jsonify({"success": False, "message": "请选择 Excel 文件"}), 400
            if not upload.filename.lower().endswith((".xlsx", ".xls")):
                return jsonify({"success": False, "message": "只支持 .xlsx/.xls 文件"}), 400

            filename = f"vector_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upload.filename}"
            file_path = os.path.join(get_upload_dir(), filename)
            upload.save(file_path)
            should_cleanup = True
            if not payload:
                payload = request.form.to_dict() or {}
        else:
            file_path = str(payload.get("file_path") or "").strip()
            should_cleanup = False

        index_name = str(payload.get("index_name") or "").strip() or None
        index_id = str(payload.get("index_id") or "").strip() or None

        result = ingest_service.ingest_excel(
            file_path=file_path,
            index_name=index_name,
            index_id=index_id,
        )

        if should_cleanup and os.path.exists(file_path):
            os.remove(file_path)

        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as err:
        logger.exception("Excel 向量化 ingest 失败: %s", err)
        return jsonify({"success": False, "message": str(err)}), 500


@excel_vector_bp.route("/query", methods=["POST"])
def query_excel_vector():
    """按 query 在指定索引中检索语义相关内容。"""
    try:
        payload = request.get_json(silent=True) or {}
        index_id = str(payload.get("index_id") or "").strip()
        query_text = str(payload.get("query") or "").strip()
        top_k = int(payload.get("top_k", 5))

        search_service = get_excel_vector_search_app_service()
        result = search_service.query(index_id=index_id, query_text=query_text, top_k=top_k)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as err:
        logger.exception("Excel 向量 query 失败: %s", err)
        return jsonify({"success": False, "message": str(err)}), 500


@excel_vector_bp.route("/indexes", methods=["GET"])
def list_excel_vector_indexes():
    """返回向量索引列表。"""
    try:
        search_service = get_excel_vector_search_app_service()
        return jsonify(search_service.list_indexes())
    except Exception as err:
        logger.exception("获取向量索引失败: %s", err)
        return jsonify({"success": False, "message": str(err)}), 500


@excel_vector_bp.route("/indexes/<string:index_id>", methods=["DELETE"])
def delete_excel_vector_index(index_id: str):
    """删除指定向量索引。"""
    try:
        search_service = get_excel_vector_search_app_service()
        result = search_service.delete_index(index_id=index_id)
        return jsonify(result), (200 if result.get("success") else 404)
    except Exception as err:
        logger.exception("删除向量索引失败: %s", err)
        return jsonify({"success": False, "message": str(err)}), 500
