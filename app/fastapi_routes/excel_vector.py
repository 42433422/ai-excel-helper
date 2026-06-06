"""Excel 向量索引 API（自归档 excel_vector 蓝图迁移）。"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app.application import get_excel_vector_ingest_app_service, get_excel_vector_search_app_service
from app.utils.path_utils import get_upload_dir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/excel/vector", tags=["excel-vector"])


@router.post("/ingest")
async def ingest_excel_vector(request: Request):
    try:
        ingest_service = get_excel_vector_ingest_app_service()
        payload: dict[str, Any] = {}
        file_path: str = ""
        should_cleanup = False

        ct = (request.headers.get("content-type") or "").lower()
        if "multipart/form-data" in ct:
            form = await request.form()
            upload = form.get("excel_file")
            if upload is not None and hasattr(upload, "filename") and upload.filename:
                if not str(upload.filename).lower().endswith((".xlsx", ".xls")):
                    return JSONResponse(
                        {"success": False, "message": "只支持 .xlsx/.xls 文件"}, status_code=400
                    )
                filename = f"vector_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upload.filename}"
                file_path = os.path.join(get_upload_dir(), filename)
                body = await upload.read()
                with open(file_path, "wb") as f:
                    f.write(body)
                should_cleanup = True
                payload = {
                    k: v for k, v in form.items() if k != "excel_file" and isinstance(v, str)
                }
            else:
                return JSONResponse(
                    {"success": False, "message": "请选择 Excel 文件"}, status_code=400
                )
        else:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            file_path = str(payload.get("file_path") or "").strip()
            if not file_path:
                return JSONResponse(
                    {"success": False, "message": "请提供 file_path 或上传 excel_file"},
                    status_code=400,
                )

        index_name = str(payload.get("index_name") or "").strip() or None
        index_id = str(payload.get("index_id") or "").strip() or None

        result = ingest_service.ingest_excel(
            file_path=file_path,
            index_name=index_name,
            index_id=index_id,
        )
        if should_cleanup and os.path.exists(file_path):
            os.remove(file_path)
        status = 200 if result.get("success") else 400
        return JSONResponse(result, status_code=status)
    except Exception as err:
        logger.exception("Excel 向量化 ingest 失败: %s", err)
        return JSONResponse({"success": False, "message": str(err)}, status_code=500)


@router.post("/query")
def query_excel_vector(data: dict[str, Any] = Body(default_factory=dict)):
    try:
        index_id = str(data.get("index_id") or "").strip()
        query_text = str(data.get("query") or "").strip()
        top_k = int(data.get("top_k", 5))
        search_service = get_excel_vector_search_app_service()
        result = search_service.query(index_id=index_id, query_text=query_text, top_k=top_k)
        status = 200 if result.get("success") else 400
        return JSONResponse(result, status_code=status)
    except Exception as err:
        logger.exception("Excel 向量 query 失败: %s", err)
        return JSONResponse({"success": False, "message": str(err)}, status_code=500)


@router.get("/indexes")
def list_excel_vector_indexes():
    try:
        search_service = get_excel_vector_search_app_service()
        return JSONResponse(search_service.list_indexes())
    except Exception as err:
        logger.exception("获取向量索引失败: %s", err)
        return JSONResponse({"success": False, "message": str(err)}, status_code=500)


@router.delete("/indexes/{index_id}")
def delete_excel_vector_index(index_id: str):
    try:
        search_service = get_excel_vector_search_app_service()
        result = search_service.delete_index(index_id=index_id)
        status = 200 if result.get("success") else 404
        return JSONResponse(result, status_code=status)
    except Exception as err:
        logger.exception("删除向量索引失败: %s", err)
        return JSONResponse({"success": False, "message": str(err)}, status_code=500)
