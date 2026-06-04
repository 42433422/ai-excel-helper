"""Migrated from legacy_products.py (v10)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, File, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy-products"], deprecated=True)


@router.delete("/api/products/{product_id}")
def products_delete(product_id: int):
    from app.bootstrap import get_products_service

    return get_products_service().delete_product(product_id)


@router.post("/api/products/import/price-list-template")
async def products_import_price_list_template(
    template_file: UploadFile | None = File(default=None),
):
    try:
        from app.infrastructure.documents.template_registry import fhd_repo_root
    except Exception as e:
        logger.exception("template_registry import failed")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

    if template_file is None or not template_file.filename:
        return JSONResponse({"success": False, "message": "请上传 .docx 模板文件"}, status_code=400)
    if not str(template_file.filename).lower().endswith(".docx"):
        return JSONResponse({"success": False, "message": "只支持 .docx 格式"}, status_code=400)
    try:
        body = await template_file.read()
    except Exception as e:
        logger.exception("price list template read failed")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
    if len(body) < 64:
        return JSONResponse({"success": False, "message": "文件过小或已损坏"}, status_code=400)
    if not body.startswith(b"PK"):
        return JSONResponse(
            {"success": False, "message": "不是有效的 Office Open XML（.docx）文件"},
            status_code=400,
        )
    try:
        dest_dir = fhd_repo_root() / "424" / "document_templates"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "price_list_default.docx"
        dest.write_bytes(body)
        rel = dest.relative_to(fhd_repo_root())
    except Exception as e:
        logger.exception("price list template write failed")
        return JSONResponse({"success": False, "message": f"保存失败：{e}"}, status_code=500)
    return {
        "success": True,
        "message": f"已保存价目表 Word 模板（{rel.as_posix()}），导出 Word 价目表时将使用该文件。",
    }


@router.get("/api/products/export.xlsx")
def products_export_xlsx(
    unit: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    template_id: str | None = Query(default=None),
):
    import os as _os

    from app.bootstrap import get_products_service

    service = get_products_service()
    result = service.export_to_excel(unit_name=unit, keyword=keyword, template_id=template_id)
    if not result.get("success"):
        return JSONResponse(result, status_code=400)
    file_path = result.get("file_path")
    filename = result.get("filename")
    if file_path and _os.path.exists(file_path):
        return FileResponse(
            file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return JSONResponse({"success": False, "message": "导出文件不存在"}, status_code=500)


@router.get("/api/products/product_names")
def products_product_names():
    from app.bootstrap import get_products_service

    return get_products_service().get_product_names()


@router.get("/api/products/product_names/search")
def products_product_names_search(keyword: str = Query(default="")):
    from app.bootstrap import get_products_service

    return get_products_service().get_product_names(keyword=keyword)


@router.get("/api/products/search")
def products_search(keyword: str = Query(default="")):
    from app.bootstrap import get_products_service

    return get_products_service().get_products(keyword=keyword)


@router.post("/api/products/batch")
def products_batch(body: dict = Body(default_factory=dict)):
    from app.bootstrap import get_products_service

    data = body or {}
    products = data.get("products") or []
    if not isinstance(products, list) or not products:
        return JSONResponse(
            {"success": False, "message": "products 必须为非空数组"}, status_code=400
        )
    service = get_products_service()
    return service.batch_add_products(products)


@router.post("/api/products/{product_id}")
def products_update_post(product_id: int, body: dict = Body(default_factory=dict)):
    from app.bootstrap import get_products_service

    service = get_products_service()
    result = service.update_product(product_id, body or {})
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.put("/api/products/{product_id}")
def products_put(product_id: int, body: dict = Body(default_factory=dict)):
    from app.bootstrap import get_products_service

    service = get_products_service()
    result = service.update_product(product_id, body or {})
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.patch("/api/products/{product_id}")
def products_patch(product_id: int, body: dict = Body(default_factory=dict)):
    from app.bootstrap import get_products_service

    service = get_products_service()
    result = service.update_product(product_id, body or {})
    return JSONResponse(result, status_code=200 if result.get("success") else 400)
