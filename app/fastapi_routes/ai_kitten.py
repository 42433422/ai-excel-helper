"""Kitten 分析/图表/报告路由。

Phase 2B 从 :mod:`app.fastapi_routes.archive_gap_batch1/2` 拆分而出,
URL 保持不变:

- ``GET /api/ai/kitten/business-snapshot``
- ``GET /api/ai/kitten/charts/{all,revenue,products,customers,profit,inventory}``
- ``GET /api/ai/kitten/saved/list`` / ``GET /api/ai/kitten/saved/{id}`` /
  ``GET /api/ai/kitten/saved/{id}/export`` / ``DELETE /api/ai/kitten/saved/{id}``
- ``POST /api/ai/kitten/financial/report`` / ``POST /api/ai/kitten/report/export`` /
  ``POST /api/ai/kitten/report/export-docx``
- ``POST /api/ai/kitten/document/generate`` / ``GET /api/ai/kitten/document/pickup/{token}``

归属理由: 小猫分析(Kitten) 是一个完整的业务域,前端 ``frontend/src/api/kitten.ts``、
``views/AIEcosystemView.vue`` 成组使用。
"""

from __future__ import annotations

import logging
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-kitten"])


@router.get("/api/ai/kitten/business-snapshot")
def kitten_business_snapshot():
    try:
        from app.application.facades.kitten_facade import build_kitten_business_snapshot

        snap = build_kitten_business_snapshot()
        return {"success": True, "data": snap}
    except Exception as e:
        logger.exception("kitten business-snapshot: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/ai/kitten/charts/all")
def kitten_charts_all():
    try:
        from app.application.facades.kitten_facade import chart_service

        return {"success": True, "data": chart_service.get_all_charts_data()}
    except Exception as e:
        logger.exception("kitten charts all: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/ai/kitten/charts/revenue")
def kitten_charts_revenue(months: int = Query(default=6)):
    try:
        from app.application.facades.kitten_facade import chart_service

        return chart_service.get_revenue_chart_data(months)
    except Exception as e:
        logger.exception("kitten revenue: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/api/ai/kitten/charts/products")
def kitten_charts_products():
    try:
        from app.application.facades.kitten_facade import chart_service

        return chart_service.get_product_pie_chart_data()
    except Exception as e:
        logger.exception("kitten products: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/api/ai/kitten/charts/customers")
def kitten_charts_customers():
    try:
        from app.application.facades.kitten_facade import chart_service

        return chart_service.get_customer_bar_chart_data()
    except Exception as e:
        logger.exception("kitten customers: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/api/ai/kitten/charts/profit")
def kitten_charts_profit(months: int = Query(default=6)):
    try:
        from app.application.facades.kitten_facade import chart_service

        return chart_service.get_profit_trend_chart_data(months)
    except Exception as e:
        logger.exception("kitten profit: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/api/ai/kitten/charts/inventory")
def kitten_charts_inventory():
    try:
        from app.application.facades.kitten_facade import chart_service

        return chart_service.get_inventory_chart_data()
    except Exception as e:
        logger.exception("kitten inventory chart: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/api/ai/kitten/saved/list")
def kitten_saved_list(type: str | None = Query(default=None)):
    try:
        from app.application.facades.kitten_facade import analysis_save_service

        analyses = analysis_save_service.list_saved_analyses(type)
        stats = analysis_save_service.get_statistics_summary()
        return {"success": True, "analyses": analyses, "statistics": stats}
    except Exception as e:
        logger.exception("kitten saved list: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/ai/kitten/saved/{analysis_id}")
def kitten_saved_get(analysis_id: str):
    try:
        from app.application.facades.kitten_facade import analysis_save_service

        analysis = analysis_save_service.get_analysis(analysis_id)
        if not analysis:
            return JSONResponse({"success": False, "message": "未找到该分析记录"}, status_code=404)
        return {"success": True, "data": analysis}
    except Exception as e:
        logger.exception("kitten saved get: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/ai/kitten/saved/{analysis_id}/export")
def kitten_saved_export(analysis_id: str):
    try:
        from app.application.facades.kitten_facade import analysis_save_service

        result = analysis_save_service.export_analysis_to_xlsx(analysis_id)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        file_name = str(result.get("file_name") or "财务报告.xlsx")
        content = result.get("content") or b""
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except Exception as e:
        logger.exception("kitten export: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.delete("/api/ai/kitten/saved/{analysis_id}")
def kitten_saved_delete(analysis_id: str):
    try:
        from app.application.facades.kitten_facade import analysis_save_service

        result = analysis_save_service.delete_analysis(analysis_id)
        if result.get("success"):
            return {"success": True, "message": "删除成功"}
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.exception("kitten delete: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/ai/kitten/financial/report")
def ai_kitten_financial_report(body: dict = Body(default_factory=dict)):
    try:
        payload = body or {}
        metadata = payload.get("metadata") or {}
        from app.application.facades.kitten_facade import (
            FinancialReportPlugin,
            InventoryValuationPlugin,
            analysis_save_service,
        )

        fin_result = FinancialReportPlugin().run(payload)
        inv_result = InventoryValuationPlugin().run(payload)
        analysis_data = {
            "financial_report": {
                "key": fin_result.key,
                "title": fin_result.title,
                "level": fin_result.level,
                "summary": fin_result.summary,
                "details": fin_result.details,
            },
            "inventory_valuation": {
                "key": inv_result.key,
                "title": inv_result.title,
                "level": inv_result.level,
                "summary": inv_result.summary,
                "details": inv_result.details,
            },
        }
        save_result = analysis_save_service.save_analysis(
            analysis_type="financial",
            data=analysis_data,
            metadata=metadata,
        )
        if save_result.get("success"):
            return {
                "success": True,
                "analysis_id": save_result.get("id"),
                "data": analysis_data,
                "saved_to": save_result.get("filename"),
                "message": "财务报告已生成并保存",
            }
        return {"success": True, "data": analysis_data, "message": "财务报告已生成（保存失败）"}
    except Exception as e:
        logger.exception("kitten financial: %s", e)
        return JSONResponse(
            {"success": False, "message": f"财务报表生成失败：{str(e)}"}, status_code=500
        )


@router.post("/api/ai/kitten/report/export")
def ai_kitten_report_export(body: dict = Body(default_factory=dict)):
    try:
        from app.application.facades.kitten_facade import KittenReportExportService

        service = KittenReportExportService()
        report = service.build_report(body or {})
        file_name = str(report.get("file_name") or "小猫分析报告.xlsx")
        content = report.get("content") or b""
        return StreamingResponse(
            BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except Exception as e:
        logger.exception("kitten export: %s", e)
        return JSONResponse({"success": False, "message": f"导出失败：{str(e)}"}, status_code=500)


@router.post("/api/ai/kitten/report/export-docx")
def ai_kitten_report_export_docx(body: dict = Body(default_factory=dict)):
    try:
        from app.application.facades.kitten_facade import build_kitten_docx

        report = build_kitten_docx(body or {})
        file_name = str(report.get("file_name") or "小猫分析报告.docx")
        content = report.get("content") or b""
        return StreamingResponse(
            BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except Exception as e:
        logger.exception("kitten docx export: %s", e)
        return JSONResponse(
            {"success": False, "message": f"Word 导出失败：{str(e)}"}, status_code=500
        )


@router.post("/api/ai/kitten/document/generate")
def kitten_document_generate(body: dict = Body(default_factory=dict)):
    """根据自然语言描述由 LLM 起草结构并生成 Word 或 Excel 文件（直接下载）。"""
    payload = body or {}
    prompt = str(payload.get("prompt") or payload.get("message") or "").strip()
    fmt = str(payload.get("format") or "docx").lower().strip()
    if fmt not in ("docx", "xlsx"):
        fmt = "docx"
    if not prompt:
        return JSONResponse(
            {"success": False, "message": "请提供文档需求描述（prompt）"}, status_code=400
        )
    try:
        from app.application.facades.kitten_facade import generate_office_file

        content, file_name = generate_office_file(prompt, fmt)  # type: ignore[arg-type]
        mime = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if fmt == "xlsx"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        ascii_name = file_name.encode("ascii", "ignore").decode("ascii") or (
            "doc.xlsx" if fmt == "xlsx" else "doc.docx"
        )
        disp = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(file_name)}"
        return StreamingResponse(
            BytesIO(content), media_type=mime, headers={"Content-Disposition": disp}
        )
    except RuntimeError as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=503)
    except Exception as e:
        logger.exception("kitten document generate: %s", e)
        return JSONResponse(
            {"success": False, "message": f"文档生成失败：{str(e)}"}, status_code=500
        )


@router.get("/api/ai/kitten/document/pickup/{token}")
def kitten_document_pickup(token: str):
    """一次性下载 Planner 工具 ``generate_office_document`` 生成的文档。"""
    from app.application.facades.kitten_facade import pop_document_pickup

    item = pop_document_pickup(token)
    if not item:
        return JSONResponse({"success": False, "message": "链接无效或已过期"}, status_code=404)
    content, file_name, mime = item
    ascii_name = file_name.encode("ascii", "ignore").decode("ascii") or "download.bin"
    disp = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(file_name)}"
    return Response(
        content=content,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": disp},
    )
