"""FastAPI lifespan：数据库、Mod、NeuroBus 启动与关闭。"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.engine import make_url

from app.db import engine
from app.db.init_db import (
    ensure_product_query_indexes,
    ensure_sessions_account_meta_columns,
    ensure_sessions_enterprise_entitlement_columns,
    ensure_sessions_market_access_token_column,
    ensure_sessions_market_refresh_token_column,
    init_approval_tables,
    init_distillation_tables,
    init_extract_logs_tables,
    init_service_bridge_tables,
    init_template_tables,
    init_wechat_tasks_table,
    initialize_databases,
)

from .sqlite_paths import is_sqlite_url, resolve_effective_database_url, sqlite_db_file_from_url

logger = logging.getLogger(__name__)

_APP_ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 应用生命周期管理"""
    logger.info("🚀 FastAPI 应用启动中...")

    from app.fastapi_app.startup_timing import mark_startup

    mark_startup("lifespan_begin")

    from app.neuro_async_bridge import set_neuro_main_loop

    set_neuro_main_loop(asyncio.get_running_loop())

    await asyncio.gather(
        _init_mods_async(app),
        _initialize_databases_async(app),
    )

    mark_startup("lifespan_db_done")

    try:
        from app.mod_sdk.desktop_deliverable import ensure_deliverable_runtime

        await ensure_deliverable_runtime(app)
    except Exception as exc:
        logger.warning("Deliverable runtime setup skipped: %s", exc)

    try:
        from app.utils.performance_initializer import init_performance_optimization

        init_performance_optimization(app)
        mark_startup("performance_optimizer_ready")
    except Exception as exc:
        logger.warning("Performance optimizer init skipped: %s", exc)

    await _init_neuro_ddd_async(app)

    mark_startup("lifespan_ready")
    logger.info("✅ FastAPI 应用启动完成")

    yield

    logger.info("🛑 FastAPI 应用关闭中...")
    try:
        from app.neuro_bus.bus_setup import teardown_neuro_bus

        await teardown_neuro_bus()
        logger.info("✅ 神经总线已关闭")
    except Exception as e:
        logger.warning("⚠️ 神经总线关闭失败: %s", e)


async def _initialize_databases_async(app: FastAPI):
    """异步初始化数据库"""
    db_url = str(getattr(app.state.config, "DATABASE_URL", "") or "").strip()
    if db_url:
        try:
            safe = make_url(db_url).render_as_string(hide_password=True)
        except (ValueError, TypeError):
            safe = db_url
        logger.info("初始化数据库... (DATABASE_URL=%s)", safe)
    else:
        logger.info("初始化数据库... (DATABASE_URL 未设置，使用默认策略)")

    await asyncio.get_running_loop().run_in_executor(None, _initialize_databases_sync, app)


def _run_ensure_ai_action_audit_table() -> None:
    """加载审计 DDL 模块但不执行 app.services 包 __init__（避免牵连全量 application / 重型依赖）。"""
    path = _APP_ROOT / "services" / "ai_action_audit_service.py"
    spec = importlib.util.spec_from_file_location("_xcagi_ai_action_audit_service", str(path))
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        raise RuntimeError("无法加载 ai_action_audit_service")
    loader.exec_module(mod)
    mod.ensure_ai_action_audit_table()


def _initialize_databases_sync(app: FastAPI):
    """同步数据库初始化（在后台线程中执行）"""
    database_url = resolve_effective_database_url(getattr(app.state.config, "DATABASE_URL", None))
    try:
        if is_sqlite_url(database_url):
            initialize_databases()
            try:
                from app.db.init_db import ensure_sqlite_per_mod_database_copies
                from app.infrastructure.mods.mod_manager import get_mod_manager

                mm = get_mod_manager()
                ids = [m.id for m in (mm.list_loaded_mods() or []) if getattr(m, "id", None)]
                if not ids:
                    ids = [m.id for m in mm.scan_mods() if getattr(m, "id", None)]
                ensure_sqlite_per_mod_database_copies(ids)
            except Exception as mod_db_exc:
                logger.warning("SQLite 按 Mod 拆分母库副本时跳过: %s", mod_db_exc)
            sqlite_file = sqlite_db_file_from_url(database_url)
            if sqlite_file:
                init_wechat_tasks_table(sqlite_file)
                init_template_tables(sqlite_file)
            else:
                init_wechat_tasks_table()
                init_template_tables()

        init_distillation_tables(engine)
        init_extract_logs_tables(engine)
        ensure_product_query_indexes(engine)
        cfg_db_url = database_url
        from app.db.init_db import ensure_runtime_auth_bootstrap

        ensure_runtime_auth_bootstrap(engine, database_url=cfg_db_url or None)
        ensure_sessions_market_access_token_column(engine, database_url=cfg_db_url or None)
        ensure_sessions_market_refresh_token_column(engine, database_url=cfg_db_url or None)
        ensure_sessions_enterprise_entitlement_columns(engine, database_url=cfg_db_url or None)
        ensure_sessions_account_meta_columns(engine, database_url=cfg_db_url or None)
        try:
            init_approval_tables(engine)
        except Exception as approval_err:
            logger.warning("approval 表初始化失败（不影响主流程）: %s", approval_err)
        try:
            init_service_bridge_tables(engine)
        except Exception as bridge_err:
            logger.warning("service_bridge 表初始化失败（不影响主流程）: %s", bridge_err)

        if not is_sqlite_url(database_url):
            try:
                from app.db.ensure_mod_postgres import ensure_postgres_per_mod_databases
                from app.infrastructure.mods.mod_manager import get_mod_manager

                mm = get_mod_manager()
                mod_ids = [m.id for m in (mm.list_loaded_mods() or []) if getattr(m, "id", None)]
                if not mod_ids:
                    mod_ids = [m.id for m in mm.scan_mods() if getattr(m, "id", None)]
                created = ensure_postgres_per_mod_databases(mod_ids=mod_ids, migrate_new=True)
                if created:
                    logger.info("已自动创建并迁移 Mod 分库: %s", ", ".join(created))
            except Exception as mod_pg_exc:
                logger.warning("PostgreSQL Mod 分库自检跳过: %s", mod_pg_exc)

        try:
            _run_ensure_ai_action_audit_table()
        except Exception as audit_err:
            logger.warning("AI审计表初始化失败（不影响主流程）: %s", audit_err)
    except Exception as e:
        safe_url = str(database_url or "").strip()
        try:
            if safe_url:
                safe_url = make_url(safe_url).render_as_string(hide_password=True)
        except (ValueError, TypeError):
            pass
        logger.exception("数据库初始化失败 (DATABASE_URL=%s): %s", safe_url or "<default>", e)
        if is_sqlite_url(database_url):
            raise RuntimeError(
                "本地数据库初始化失败：请检查 userData/data/xcagi.db 权限或磁盘空间。"
            ) from e
        raise RuntimeError(
            "数据库初始化失败：请确认 PostgreSQL 已启动且 DATABASE_URL 可连通。"
        ) from e


async def _init_neuro_ddd_async(app: FastAPI):
    """异步初始化 NeuroBus，并注册默认意图域（与对话意图桥接共用）。"""
    import os

    raw = os.environ.get("XCAGI_NEURO_INTENT", "1").strip().lower()
    if raw in {"0", "false", "off", "no"}:
        logger.info(
            "神经总线未启用（XCAGI_NEURO_INTENT=%s）", os.environ.get("XCAGI_NEURO_INTENT", "")
        )
        return
    try:
        from app.neuro_bus.bus_setup import get_neuro_bus_manager
        from app.neuro_bus.register_runtime import register_neuro_runtime

        bus = await register_neuro_runtime()
        app.state.neuro_bus = bus
        app.state.neuro_bus_manager = get_neuro_bus_manager()
        logger.info("✅ 神经总线已启动，域: %s", bus.registered_domains)
    except Exception as e:
        logger.warning("⚠️ 神经总线初始化失败: %s", e)


async def _init_mods_async(app: FastAPI):
    """初始化 Mod 扩展（create_fastapi_app 已分阶段挂载；此处仅补偿失败重试）。"""
    if getattr(app.state, "mods_full_load_done", False):
        logger.info("Mod extensions fully loaded; skipping lifespan mod init")
        return
    if getattr(app.state, "mods_background_load_scheduled", False):
        logger.info("Mod background load in progress; skipping lifespan duplicate load")
        return
    if getattr(app.state, "mods_routes_loaded", False):
        logger.info("Mod routes staged; skipping lifespan full sync load")
        return
    try:
        from app.fastapi_app.mod_startup import bootstrap_mod_extensions_sync

        await asyncio.to_thread(bootstrap_mod_extensions_sync, app)
        logger.info("✅ Mod 扩展分阶段加载已启动（lifespan 补偿路径）")
    except Exception as e:
        logger.warning("⚠️ Mod 扩展初始化失败: %s", e)
