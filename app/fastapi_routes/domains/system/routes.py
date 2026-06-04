"""Migrated from legacy_system.py (v10)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from app.template_analysis_progress import get_template_analysis_progress
from app.utils.path_utils import get_base_dir

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy-system"], deprecated=True)


@router.get("/api/system/config")
def system_config_get():
    try:
        from resources.config import industry_config as ic

        return {
            "success": True,
            "data": {
                "current_industry": ic.get_current_industry(),
                "available_industries": ic.get_available_industries(),
            },
        }
    except Exception as e:
        logger.exception("system config: %s", e)
        return {
            "success": True,
            "data": {
                "current_industry": "涂料",
                "available_industries": [{"id": "涂料", "name": "涂料/油漆行业"}],
                "degraded": True,
                "hint": (str(e) or "error")[:300],
            },
        }


@router.get("/api/system/info")
def system_info_get():
    try:
        from app.application.facades.session_facade import get_system_service

        return {"success": True, "data": get_system_service().get_system_info()}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/system/printer")
def system_printer_get():
    try:
        from app.application.facades.session_facade import get_system_service

        return {"success": True, "data": get_system_service().get_printer_config()}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/system/printer")
def system_printer_post(body: dict = Body(default_factory=dict)):
    from app.application.facades.session_facade import get_system_service

    data = body or {}
    if not data:
        return JSONResponse({"success": False, "message": "请求数据不能为空"}, status_code=400)
    printer_name = data.get("printer_name")
    if not printer_name:
        return JSONResponse(
            {"success": False, "message": "缺少参数：printer_name"}, status_code=400
        )
    result = get_system_service().set_default_printer(printer_name)
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.get("/api/system/startup")
def system_startup_get():
    try:
        from app.application.facades.session_facade import get_system_service

        return {"success": True, "data": get_system_service().get_startup_config()}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/system/startup")
def system_startup_post():
    from app.application.facades.session_facade import get_system_service

    result = get_system_service().enable_startup()
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.delete("/api/system/startup")
def system_startup_delete():
    try:
        from app.application.facades.session_facade import get_system_service

        result = get_system_service().disable_startup()
        return JSONResponse(result, status_code=200 if result.get("success") else 500)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/database/backups")
def database_backups_list():
    try:
        from app.application.facades.session_facade import get_database_service

        return get_database_service().list_backups()
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.delete("/api/database/backup/{backup_file:path}")
def database_backup_delete(backup_file: str):
    try:
        from app.application.facades.session_facade import get_database_service

        result = get_database_service().delete_backup(backup_file)
        return JSONResponse(result, status_code=200 if result.get("success") else 500)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/database/backup")
def database_backup():
    try:
        from app.application.facades.session_facade import get_database_service

        db_service = get_database_service()
        result = db_service.backup_database()
        return JSONResponse(result, status_code=200 if result.get("success") else 500)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/database/restore")
def database_restore(body: dict = Body(default_factory=dict)):
    try:
        from app.application.facades.session_facade import get_database_service

        data = body or {}
        backup_file = data.get("backup_file")
        if not backup_file:
            return JSONResponse(
                {"success": False, "message": "缺少参数：backup_file"},
                status_code=400,
            )
        db_service = get_database_service()
        result = db_service.restore_database(backup_file)
        return JSONResponse(result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/performance/status")
def performance_status():
    import time as _time

    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer._initialized:
            return JSONResponse(
                {"success": False, "message": "性能优化系统未初始化", "data": None},
                status_code=503,
            )
        return {"success": True, "data": optimizer.get_status(), "timestamp": _time.time()}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e), "data": None}, status_code=500)


@router.get("/api/performance/health")
def performance_health():
    import time as _time

    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        health = optimizer.get_health_check()
        code = (
            200
            if health["status"] == "healthy"
            else (503 if health["status"] == "degraded" else 500)
        )
        resp = {
            "status": health["status"],
            "timestamp": health["timestamp"],
            "checks": health.get("checks", {}),
        }
        if "issues" in health:
            resp["issues"] = health["issues"]
        return JSONResponse(resp, status_code=code)
    except Exception as e:
        return JSONResponse(
            {"status": "unhealthy", "error": str(e), "timestamp": _time.time()},
            status_code=500,
        )


@router.get("/api/performance/metrics/summary")
def performance_metrics_summary(minutes: int = Query(default=5)):
    try:
        minutes = max(1, min(minutes, 60))
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.performance_monitor:
            return JSONResponse(
                {"success": False, "message": "性能监控未启用", "data": None},
                status_code=503,
            )
        summary = optimizer.performance_monitor.get_metrics_summary(minutes=minutes)
        return {"success": True, "data": summary}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e), "data": None}, status_code=500)


@router.get("/api/performance/metrics/prometheus")
def performance_metrics_prometheus():
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.performance_monitor:
            return PlainTextResponse("# XCAGI metrics unavailable\n", status_code=503)
        return PlainTextResponse(
            optimizer.performance_monitor.get_prometheus_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except Exception as e:
        return PlainTextResponse(f"# Error: {str(e)}\n", status_code=500)


@router.get("/api/performance/cache/stats")
def performance_cache_stats():
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.redis_cache:
            return JSONResponse(
                {"success": False, "message": "Redis 缓存未初始化", "data": None},
                status_code=503,
            )
        return {"success": True, "data": optimizer.redis_cache.stats}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e), "data": None}, status_code=500)


@router.post("/api/performance/cache/clear")
def performance_cache_clear(pattern: str | None = Query(default=None)):
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.redis_cache:
            return JSONResponse(
                {"success": False, "message": "Redis 缓存未初始化"}, status_code=503
            )
        if pattern:
            cleared = optimizer.redis_cache.clear_pattern(pattern)
            message = f"已清除模式 '{pattern}' 的缓存 ({cleared} 个键)"
        else:
            optimizer.redis_cache.clear_local_cache()
            message = "已清除本地缓存"
        return {"success": True, "message": message}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/performance/cache/invalidate")
def performance_cache_invalidate(body: dict = Body(default_factory=dict)):
    try:
        data = body or {}
        keys = data.get("keys", [])
        if not keys:
            return JSONResponse(
                {"success": False, "message": "请提供要失效的键列表"}, status_code=400
            )
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.redis_cache:
            return JSONResponse(
                {"success": False, "message": "Redis 缓存未初始化"}, status_code=503
            )
        deleted = optimizer.redis_cache.delete(*keys)
        return {
            "success": True,
            "data": {"deleted_count": deleted, "requested_keys": len(keys)},
            "message": f"已删除 {deleted} 个缓存键",
        }
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/performance/tasks/status")
def performance_tasks_status(task_id: str | None = Query(default=None)):
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.async_task_manager:
            return JSONResponse(
                {"success": False, "message": "异步任务管理未启用", "data": None},
                status_code=503,
            )
        if task_id:
            result = optimizer.async_task_manager.get_status(task_id)
            if result is None:
                return JSONResponse(
                    {"success": False, "message": "任务不存在", "data": None},
                    status_code=404,
                )
            return {
                "success": True,
                "data": {
                    "task_id": result.task_id,
                    "status": result.status.value,
                    "progress": result.progress,
                    "duration_ms": round(result.duration_ms, 2) if result.duration_ms else None,
                    "error": result.error,
                    "metadata": result.metadata,
                },
            }
        active_tasks = optimizer.async_task_manager.active_tasks
        stats = optimizer.async_task_manager.stats
        return {
            "success": True,
            "data": {
                "active_tasks": (
                    {
                        tid: {
                            "task_id": t.task_id,
                            "status": t.status.value,
                            "progress": t.progress,
                            "name": t.metadata.get("task_name", ""),
                        }
                        for tid, t in (active_tasks or {}).items()
                    }
                    if active_tasks
                    else {}
                ),
                "stats": stats,
            },
        }
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e), "data": None}, status_code=500)


@router.get("/api/performance/alerts")
def performance_alerts(level: str | None = Query(default=None), limit: int = Query(default=20)):
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.performance_monitor:
            return JSONResponse(
                {"success": False, "message": "性能监控未启用", "data": []},
                status_code=503,
            )
        alerts = optimizer.performance_monitor.get_alerts(level=level, limit=limit)
        return {"success": True, "data": alerts, "count": len(alerts)}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e), "data": []}, status_code=500)


@router.get("/api/performance/slow-queries")
def performance_slow_queries(limit: int = Query(default=20)):
    try:
        from app.utils.performance_initializer import get_performance_optimizer

        optimizer = get_performance_optimizer()
        if not optimizer.query_optimizer:
            return JSONResponse(
                {"success": False, "message": "查询优化器未启用", "data": []},
                status_code=503,
            )
        slow = optimizer.query_optimizer.get_slow_queries(limit=limit)
        return {"success": True, "data": slow, "count": len(slow)}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e), "data": []}, status_code=500)


@router.post("/api/performance/optimize/reinitialize")
def performance_optimize_reinitialize():
    try:
        from app.utils.performance_initializer import init_performance_optimization

        optimizer = init_performance_optimization()
        return {
            "success": True,
            "message": "性能优化系统已重新初始化",
            "data": optimizer.get_status(),
        }
    except Exception as e:
        logger.exception("performance reinit: %s", e)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/templates/progress/{task_id}")
def templates_progress(task_id: str):
    return get_template_analysis_progress(task_id)


@router.delete("/api/templates/delete")
def templates_delete(request: Request, body: dict = Body(default_factory=dict)):
    try:
        import os as _os
        from datetime import datetime

        from sqlalchemy import text

        from app.db.init_db import init_template_tables
        from app.db.session import get_db

        template_id = str(body.get("id") or request.query_params.get("id") or "").strip()
        if not template_id:
            return JSONResponse({"success": False, "message": "缺少模板 id"}, status_code=400)
        if template_id.startswith("fs:"):
            filename = template_id.split(":", 1)[1].strip()
            if not filename:
                return JSONResponse(
                    {"success": False, "message": "模板文件名无效"}, status_code=400
                )
            base_dir = get_base_dir()
            candidates = [
                _os.path.join(base_dir, filename),
                _os.path.join(base_dir, "templates", filename),
                _os.path.join(base_dir, "resources", "templates", filename),
            ]
            target_path = None
            for p in candidates:
                if _os.path.isfile(p):
                    target_path = p
                    break
            if not target_path:
                return JSONResponse(
                    {"success": False, "message": f"模板文件不存在: {filename}"}, status_code=404
                )
            _os.remove(target_path)
            return {
                "success": True,
                "message": "模板删除成功",
                "deleted": {"id": template_id, "path": target_path},
            }
        db_id = None
        if template_id.startswith("db:"):
            raw_db_id = template_id.split(":", 1)[1].strip()
            if raw_db_id.isdigit():
                db_id = int(raw_db_id)
        elif template_id.isdigit():
            db_id = int(template_id)
        if db_id is not None:
            try:
                init_template_tables()
            except Exception:
                pass
            with get_db() as db:
                row = db.execute(
                    text("SELECT id FROM templates WHERE id = :id"), {"id": db_id}
                ).fetchone()
                if not row:
                    return JSONResponse(
                        {"success": False, "message": "模板不存在"}, status_code=404
                    )
                db.execute(
                    text(
                        "UPDATE templates SET is_active = 0, updated_at = :updated_at WHERE id = :id"
                    ),
                    {"id": db_id, "updated_at": datetime.now()},
                )
                db.commit()
            return {
                "success": True,
                "message": "模板删除成功",
                "deleted": {"id": template_id, "db_id": db_id},
            }
        return JSONResponse(
            {"success": False, "message": f"暂不支持删除该模板类型: {template_id}"}, status_code=400
        )
    except Exception as e:
        return JSONResponse({"success": False, "message": f"删除失败：{str(e)}"}, status_code=500)


@router.post("/api/templates/create")
def templates_create(body: dict = Body(default_factory=dict)):
    from app.routes.document_templates_compat import run_archive_template_create

    data, code = run_archive_template_create(body)
    return JSONResponse(data, status_code=code)


@router.post("/api/templates/update")
def templates_update(body: dict = Body(default_factory=dict)):
    from app.routes.document_templates_compat import run_archive_template_update

    data, code = run_archive_template_update(body)
    return JSONResponse(data, status_code=code)


@router.post("/api/templates/delete")
def templates_delete_post(request: Request, body: dict = Body(default_factory=dict)):
    return templates_delete(request, body)


@router.post("/api/templates/analyze")
async def templates_analyze(
    file: UploadFile = File(...),
    template_name: str = Form(default=""),
    template_scope: str = Form(default=""),
):
    from app.routes.document_templates_compat import run_archive_template_analyze

    raw = await file.read()
    data, code = run_archive_template_analyze(
        file_body=raw,
        filename=file.filename or "upload.bin",
        template_name=template_name,
        template_scope=template_scope,
    )
    return JSONResponse(data, status_code=code)


@router.get("/api/skills/list")
def skills_list():
    try:
        from app.infrastructure.skills import get_skill_registry

        registry = get_skill_registry()
        return {"success": True, "skills": registry.list_all()}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/skills/info/{skill_id}")
def skills_info(skill_id: str):
    try:
        from app.infrastructure.skills import get_skill_registry

        registry = get_skill_registry()
        skill_info = registry.get(skill_id)
        if skill_info:
            return {
                "success": True,
                "skill": {
                    "id": skill_id,
                    "name": skill_info.get("name", ""),
                    "description": skill_info.get("description", ""),
                    "keywords": skill_info.get("keywords", []),
                    "category": skill_info.get("category", "general"),
                },
            }
        return JSONResponse({"success": False, "message": "技能不存在"}, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/skills/execute")
def skills_execute(body: dict = Body(default_factory=dict)):
    from app.routes.tools import run_archive_tools_execute

    data, code = run_archive_tools_execute(body)
    return JSONResponse(data, status_code=code)


@router.post("/api/tools/execute")
def tools_execute_route(body: dict = Body(default_factory=dict)):
    from app.routes.tools import run_archive_tools_execute

    data, code = run_archive_tools_execute(body)
    return JSONResponse(data, status_code=code)


@router.post("/api/admin/llm/reload")
async def admin_llm_reload() -> JSONResponse:
    """热切换：清空进程内 LLM Provider 注册表。"""
    import os

    from app.infrastructure.llm.providers import registry as reg_mod

    reg_mod._registry = None  # type: ignore[attr-defined]
    return JSONResponse(
        {
            "success": True,
            "LLM_PROVIDER": (os.environ.get("LLM_PROVIDER") or "").strip(),
            "LLM_ROUTING_ORDER": (os.environ.get("LLM_ROUTING_ORDER") or "").strip(),
        }
    )
