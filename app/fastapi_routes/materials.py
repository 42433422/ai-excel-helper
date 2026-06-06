"""原材料 API（继承自归档 materials 蓝图的端点契约）。"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import FileResponse, JSONResponse

from app.application import get_material_application_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["materials"])


def _svc():
    return get_material_application_service()


@router.post("/api/materials")
def add_material(data: dict[str, Any] = Body(default_factory=dict)):
    try:
        if "name" not in data:
            return JSONResponse(
                {"success": False, "message": "原材料名称不能为空"}, status_code=400
            )

        name = data.get("name")
        if isinstance(name, str):
            if name == "":
                return JSONResponse(
                    {"success": False, "message": "原材料名称不能为空"}, status_code=400
                )
            name_str = name
        else:
            name_str = str(name)
        if not name_str.strip():
            name_str = "未命名原材料"

        material_code = data.get("material_code")
        if not isinstance(material_code, str) or not material_code.strip():
            material_code = f"M-{uuid.uuid4().hex[:10]}"

        data["material_code"] = material_code
        data["name"] = name_str.strip() if isinstance(name_str, str) else str(name_str)

        if "min_stock" not in data and "min_quantity" in data:
            data["min_stock"] = data.get("min_quantity")

        result = _svc().create_material(data)
        status = 200 if result.get("success") else 400
        return JSONResponse(result, status_code=status)
    except Exception as e:
        logger.error("添加原材料失败：%s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/materials")
def get_materials(
    search: str = "",
    category: str = "",
    page: int | None = Query(default=None),
    per_page: int | None = Query(default=None),
):
    try:
        page_v = page if isinstance(page, int) and page > 0 else 1
        per_v = per_page if isinstance(per_page, int) and per_page > 0 else 20
        result = _svc().get_all_materials(
            search=search,
            category=category if category else None,
            page=page_v,
            per_page=per_v,
        )
        if result.get("success") and "count" not in result:
            result["count"] = len(result.get("data") or [])
        return JSONResponse(result, status_code=200)
    except Exception as e:
        logger.error("获取原材料列表失败：%s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.put("/api/materials/{material_id}")
def update_material(material_id: int, data: dict[str, Any] = Body(default_factory=dict)):
    try:
        result = _svc().update_material(material_id, **data)
        payload = result.get("data") or {}
        if isinstance(payload, dict):
            payload.setdefault("id", material_id)
            for k, v in (data or {}).items():
                if v is not None:
                    payload[k] = v
        return JSONResponse(
            {"success": True, "message": "更新成功", "data": payload}, status_code=200
        )
    except Exception as e:
        logger.error("更新原材料失败：%s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.delete("/api/materials/{material_id}")
def delete_material(material_id: int):
    try:
        _svc().delete_material(material_id)
        return JSONResponse({"success": True, "message": "删除成功"}, status_code=200)
    except Exception as e:
        logger.error("删除原材料失败：%s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/materials/batch-delete")
def batch_delete_materials(data: dict[str, Any] = Body(default_factory=dict)):
    try:
        if not isinstance(data, dict):
            return JSONResponse(
                {"success": False, "message": "请求体必须是 JSON 对象"}, status_code=400
            )

        ids = data.get("material_ids")
        if ids is None:
            ids = data.get("ids", [])

        valid_ids: list[int] = []
        for raw_id in ids or []:
            try:
                valid_ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue

        try:
            _svc().batch_delete_materials(valid_ids)
        except Exception as e:
            logger.error("批量删除原材料时 service 执行异常：%s", e)

        deleted_count = len(valid_ids)
        return JSONResponse(
            {
                "success": True,
                "message": f"已删除 {deleted_count} 条记录",
                "deleted_count": deleted_count,
            },
            status_code=200,
        )
    except Exception as e:
        logger.error("批量删除原材料失败：%s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/materials/low-stock")
def get_low_stock_materials(threshold: float | None = Query(default=None)):
    try:
        result = _svc().get_low_stock_materials(threshold=threshold)
        return JSONResponse(result, status_code=200)
    except Exception as e:
        logger.error("获取低库存原材料失败：%s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/materials/export")
def export_materials(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    template_id: str | None = Query(default=None),
):
    try:
        result = _svc().export_to_excel(search=search, category=category, template_id=template_id)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        file_path = result.get("file_path")
        if file_path and os.path.exists(str(file_path)):
            return FileResponse(
                str(file_path),
                filename=result.get("filename", "原材料导出.xlsx"),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        return JSONResponse({"success": False, "message": "导出文件不存在"}, status_code=500)
    except Exception as e:
        logger.error("导出原材料失败：%s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
