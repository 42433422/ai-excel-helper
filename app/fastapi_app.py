"""
FastAPI 应用工厂

创建和配置 FastAPI 应用实例。

.. note::
    Python 会优先加载 **包** ``app/fastapi_app/``（``factory.py`` / ``lifespan.py``），
    本文件 **不会** 作为 ``import app.fastapi_app`` 的目标被导入。
    生命周期与启动逻辑请改 ``app/fastapi_app/lifespan.py`` 等包内模块。
"""

import sys
from pathlib import Path


def _ensure_repo_root_on_sys_path() -> None:
    """把含 ``app`` 包的仓库根加入 ``sys.path``。

    ``XCAGI/app`` 可能为指向 ``<repo>/app`` 的目录联接,此时 ``__file__`` 仍带
    ``.../XCAGI/app/...`` 前缀;若只按 ``parents[1]`` 推断会得到 ``XCAGI`` 而非
    仓库根,导致 ``import app.<sub>`` 需要的顶层 ``app`` 在某些调用场景下定位失败。
    """

    here = Path(__file__).resolve()
    for p in here.parents:
        try:
            if (p / "app" / "fastapi_app.py").is_file() and (p / "app" / "fastapi_routes").is_dir():
                s = str(p)
                if s not in sys.path:
                    sys.path.insert(0, s)
                return
        except OSError:
            continue


_ensure_repo_root_on_sys_path()

import asyncio
import inspect
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import make_url

from app.config import Config, get_config
from app.db import engine
from app.db.init_db import (
    ensure_product_query_indexes,
    ensure_sessions_market_access_token_column,
    ensure_sessions_market_refresh_token_column,
    ensure_sessions_enterprise_entitlement_columns,
    ensure_sessions_account_meta_columns,
    init_approval_tables,
    init_service_bridge_tables,
    init_distillation_tables,
    init_extract_logs_tables,
    init_template_tables,
    init_wechat_tasks_table,
    initialize_databases,
)
from app.infrastructure.mods.mod_auth import ModContextMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.xss_sanitizer import XSSSanitizerMiddleware
from app.request_active_mod_ctx import (
    parse_active_mod_header,
    reset_request_active_mod_id,
    set_request_active_mod_id,
)
from app.security import LanCidrGuard, LanLicenseGuard
from app.utils.path_utils import get_base_dir

logger = logging.getLogger(__name__)


def resolve_cors_allow_origins() -> list[str]:
    raw = (os.environ.get("CORS_ALLOW_ORIGINS") or "").strip()
    if raw:
        # 与 allow_credentials=True 组合时，浏览器禁止 Access-Control-Allow-Origin: *
        origins = [x.strip() for x in raw.split(",") if x.strip() and x.strip() != "*"]
        if origins:
            return origins
    return [
        "http://127.0.0.1:5001",
        "http://localhost:5001",
        "http://127.0.0.1:5101",
        "http://localhost:5101",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]


def _lan_origin_regex_enabled() -> bool:
    """是否启用私网 Origin 正则（手机 / 平板用 http://192.168.*.*:5001 打开前端时 CORS 预检需要）。"""
    raw = (os.environ.get("XCAGI_DEV_ALLOW_LAN_CORS") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    # 未显式配置：与 XCAGI_DEBUG 默认 1 对齐，避免「没用启动器」时局域网全被 CORS 拦死
    return os.environ.get("XCAGI_DEBUG", "1").strip() == "1"


def resolve_cors_allow_origin_regex() -> str | None:
    """
    与 allow_origins 并列；用于开发机局域网 IP 访问 Vite（如 http://192.168.1.2:5001）
    且带 credentials 的 API 预检。生产请设 XCAGI_DEBUG=0，并显式配置 CORS_ALLOW_ORIGINS。
    """
    explicit = (os.environ.get("CORS_ALLOW_ORIGIN_REGEX") or "").strip()
    if explicit:
        return explicit
    if _lan_origin_regex_enabled():
        return (
            r"^http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
        )
    return None


def _is_sqlite_url(database_url: str | None) -> bool:
    return str(database_url or "").strip().startswith("sqlite")


def _sqlite_db_file_from_url(database_url: str | None) -> str | None:
    """从 DATABASE_URL 解析 SQLite 文件路径"""
    if not _is_sqlite_url(database_url):
        return None
    raw = str(database_url).strip()
    prefix = "sqlite:///"
    if not raw.startswith(prefix):
        return None
    path = raw[len(prefix) :].split("?", 1)[0].strip()
    if not path or path == ":memory:":
        return None
    # 兼容 Windows 路径
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return os.path.abspath(path.replace("/", os.sep))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 应用生命周期管理"""
    logger.info("🚀 FastAPI 应用启动中...")

    from app.neuro_async_bridge import set_neuro_main_loop

    set_neuro_main_loop(asyncio.get_running_loop())

    # Mod 扫描/import 耗 CPU 与 IO，放到线程池；与数据库初始化并行以缩短首包可响应时间
    await asyncio.gather(
        _init_mods_async(app),
        _initialize_databases_async(app),
    )

    # 初始化 Neuro-DDD 总线（如果启用）
    await _init_neuro_ddd_async(app)

    logger.info("✅ FastAPI 应用启动完成")

    # 后台定时任务：每 5 分钟扫描一次审批超时
    _approval_timeout_task = asyncio.create_task(_approval_timeout_loop())

    yield

    _approval_timeout_task.cancel()
    try:
        await _approval_timeout_task
    except asyncio.CancelledError:
        pass

    # 应用关闭
    logger.info("🛑 FastAPI 应用关闭中...")
    try:
        from app.neuro_bus.bus_setup import teardown_neuro_bus

        await teardown_neuro_bus()
        logger.info("✅ 神经总线已关闭")
    except Exception as e:
        logger.warning("⚠️ 神经总线关闭失败: %s", e)


async def _approval_timeout_loop() -> None:
    """每 5 分钟扫描一次超时审批请求（自动拒绝/通过）。"""
    await asyncio.sleep(60)  # 启动后 1 分钟再开始
    while True:
        try:
            from app.application.workflow.approval_service import process_approval_timeouts

            result = process_approval_timeouts()
            if result.get("processed"):
                logger.info("审批超时处理完成: %s 条", result.get("processed"))
        except Exception as e:
            logger.debug("审批超时循环异常（非致命）: %s", e)
        await asyncio.sleep(300)  # 5 分钟


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

    # 使用线程池执行同步数据库操作（须在协程内使用 get_running_loop）
    await asyncio.get_running_loop().run_in_executor(None, _initialize_databases_sync, app)


def _run_ensure_ai_action_audit_table() -> None:
    """加载审计 DDL 模块但不执行 app.services 包 __init__（避免牵连全量 application / 重型依赖）。"""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent / "services" / "ai_action_audit_service.py"
    spec = importlib.util.spec_from_file_location("_xcagi_ai_action_audit_service", str(path))
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        raise RuntimeError("无法加载 ai_action_audit_service")
    loader.exec_module(mod)
    mod.ensure_ai_action_audit_table()


def _initialize_databases_sync(app: FastAPI):
    """同步数据库初始化（在后台线程中执行）"""
    database_url = getattr(app.state.config, "DATABASE_URL", None)
    try:
        if _is_sqlite_url(database_url):
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
            sqlite_file = _sqlite_db_file_from_url(database_url)
            if sqlite_file:
                init_wechat_tasks_table(sqlite_file)
                init_template_tables(sqlite_file)
            else:
                init_wechat_tasks_table()
                init_template_tables()

        init_distillation_tables(engine)
        init_extract_logs_tables(engine)
        ensure_product_query_indexes(engine)
        cfg_db_url = str(getattr(app.state.config, "DATABASE_URL", "") or "").strip()
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
    """初始化 Mod 扩展（通常在 create_fastapi_app 已同步挂载路由；此处仅补偿失败重试）。"""
    if getattr(app.state, "mods_routes_loaded", False):
        logger.info("Mod routes already mounted before SPA fallback; skipping lifespan mod init")
        return
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, load_mod_routes

        mm = get_mod_manager()
        await asyncio.to_thread(mm.load_all_mods)
        load_mod_routes(app, mm)
        app.state.mods_routes_loaded = True
        logger.info("✅ Mod 扩展加载完成（lifespan 补偿路径）")
    except Exception as e:
        logger.warning(f"⚠️ Mod 扩展初始化失败: {e}")


def _mount_vue_dist_public_static(app: FastAPI) -> None:
    """挂载与 Vite ``public/`` 对齐的根路径静态目录（须在 SPA fallback 之前）。"""
    vue_dist = os.path.join(get_base_dir(), "templates", "vue-dist")
    if not os.path.isdir(vue_dist):
        logger.warning("Vue dist 目录不存在，跳过 public 静态挂载: %s", vue_dist)
        return
    for sub in ("font-awesome", "startup", "yuangong", "workflow"):
        directory = os.path.join(vue_dist, sub)
        if not os.path.isdir(directory):
            continue
        mount_path = f"/{sub}"
        try:
            app.mount(mount_path, StaticFiles(directory=directory), name=f"vue-dist-{sub}")
            logger.info("Mounted Vue static: %s -> %s", mount_path, directory)
        except Exception as e:
            logger.warning("挂载 %s 失败: %s", mount_path, e)


def _mount_vue_dist_assets_dir(app: FastAPI) -> None:
    """挂载 Vite 产物 ``vue-dist/assets`` 到 ``/assets``（须在 SPA fallback 之前）。

    使用 Starlette ``StaticFiles`` 提供字体/CSS 分片等，避免手写 FileResponse 的 MIME/边缘问题；
    与 LAN 中间件的 ``/assets/`` 白名单一致。
    """
    vue_dist = os.path.join(get_base_dir(), "templates", "vue-dist")
    assets_dir = os.path.join(vue_dist, "assets")
    if not os.path.isdir(assets_dir):
        logger.warning("Vue dist assets 目录不存在，跳过 /assets 挂载: %s", assets_dir)
        return
    try:
        app.mount("/assets", StaticFiles(directory=assets_dir), name="vue_dist_assets")
        logger.info("Mounted Vue dist assets: /assets -> %s", assets_dir)
    except Exception as e:
        logger.warning("挂载 /assets 失败: %s", e)


def create_fastapi_app(
    config_object: type[Config] | None = None,
    enable_cors: bool = True,
    enable_docs: bool = True,
) -> FastAPI:
    """
    创建并配置 FastAPI 应用实例

    Args:
        config_object: 配置类
        enable_cors: 是否启用 CORS
        enable_docs: 是否启用 API 文档

    Returns:
        配置好的 FastAPI 应用实例
    """
    # 加载配置
    if config_object is None:
        config_object = get_config("default")

    from app.infrastructure.cache.wiring import wire_cache_port

    wire_cache_port()

    if not getattr(config_object, "SECRET_KEY", None):
        is_debug = getattr(config_object, "DEBUG", False)
        is_desktop = getattr(config_object, "DESKTOP_MODE", False)
        if not is_debug and not is_desktop:
            raise RuntimeError(
                "SECRET_KEY must be set in production. "
                "Set the SECRET_KEY environment variable or use DevelopmentConfig for local development."
            )

    # 创建 FastAPI 应用
    app = FastAPI(
        title="XCAGI FastAPI",
        description="XCAGI 企业 AI 员工平台 - FastAPI 版本",
        version="8.0.0",
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        lifespan=lifespan,
    )

    # 存储配置到应用状态
    app.state.config = config_object

    from app.di.registry import get_service_registry

    app.state.services = get_service_registry()

    # 配置 CORS（勿与 allow_credentials 同时使用 allow_origins=["*"]）
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(XSSSanitizerMiddleware)

    if enable_cors:
        _cors_regex = resolve_cors_allow_origin_regex()
        _cors_kw: dict = dict(
            allow_origins=resolve_cors_allow_origins(),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
        if _cors_regex:
            _cors_kw["allow_origin_regex"] = _cors_regex
        # Chrome「专用网络访问」预检会带 Access-Control-Request-Private-Network；不回应则 CORS 预检 400，手机端整页进不去
        if (
            _lan_origin_regex_enabled()
            and "allow_private_network" in inspect.signature(CORSMiddleware).parameters
        ):
            _cors_kw["allow_private_network"] = True
        app.add_middleware(CORSMiddleware, **_cors_kw)

    # Mod 上下文（纯 ASGI，避免 Starlette BaseHTTPMiddleware 的流式/阻塞边缘问题）
    app.add_middleware(ModContextMiddleware)

    # LAN 授权门禁：先 license 后 cidr，但中间件按"先注册=最后执行"链式调用，
    # 因此先 add license guard 再 add cidr guard，最终请求顺序是 CIDR → License → Mod → Routes。
    app.add_middleware(LanLicenseGuard)
    app.add_middleware(LanCidrGuard)

    # 配置日志
    logging.basicConfig(
        level=getattr(config_object, "LOG_LEVEL", "INFO"),
        format=getattr(
            config_object, "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
    )

    try:
        from app.desktop_runtime import is_desktop_mode

        if is_desktop_mode():
            log_dir = os.environ.get("XCAGI_LOG_DIR")
            if log_dir:
                from app.desktop_runtime.logging_setup import attach_desktop_file_logging

                attach_desktop_file_logging(log_dir)
    except Exception as exc:
        logger.warning("Desktop file logging setup skipped: %s", exc)

    # 注册路由(``register_all_routes`` 内部已合并原 ``fastapi_compat_routes`` 中的历史兼容路由)
    from app.fastapi_routes import register_all_routes

    register_all_routes(app)

    # 注册异常处理器
    from app.middleware.error_handler import register_exception_handlers

    register_exception_handlers(app)

    # 注册中间件
    _register_middleware(app)

    # 注册 Prometheus 监控端点
    _register_prometheus_metrics(app)

    # Mod 的 HTTP 路由必须在 Vue SPA catch-all（``/{fallback:path}``）之前注册。
    # 若仅在 lifespan 里异步挂载，部分环境下 /api/mod/<id>/... 会先命中兜底并返回「资源不存在」。
    app.state.mods_routes_loaded = False
    try:
        from app.infrastructure.mods.mod_manager import (
            get_mod_manager,
            is_mods_disabled,
            load_mod_routes,
        )

        if not is_mods_disabled():
            mm = get_mod_manager()
            mm.load_all_mods()
            load_mod_routes(app, mm)
            app.state.mods_routes_loaded = True
            logger.info("Mod extensions loaded before SPA history fallback")
    except Exception as e:
        logger.warning("Mod extensions sync load failed (lifespan may retry): %s", e)

    _mount_vue_dist_public_static(app)
    _mount_vue_dist_assets_dir(app)

    try:
        from app.fastapi_routes.spa_fallback import register_spa_history_fallback

        register_spa_history_fallback(app)
        logger.info("Registered Vue history fallback (/{fallback:path}) as the last route")
    except Exception as e:
        logger.exception("Failed to register SPA history fallback: %s", e)
        raise

    return app


def _register_middleware(app: FastAPI):
    """注册中间件"""

    @app.middleware("http")
    async def http_request_context(request: Request, call_next):
        """位于链路的内层：在路由执行前绑定 ``Request``，结束后重置 ContextVar。"""
        from app.http.request_context import reset_current_http_request, set_current_http_request

        token = set_current_http_request(request)
        try:
            return await call_next(request)
        finally:
            reset_current_http_request(token)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """请求日志中间件"""
        logger.info(f"FastAPI Request: {request.method} {request.url}")
        active_mod = parse_active_mod_header(request.headers)
        if active_mod:
            try:
                from app.db.host_base_db_api import should_use_base_database_for_path

                if should_use_base_database_for_path(request.url.path):
                    active_mod = ""
            except Exception:
                pass
        am_token = set_request_active_mod_id(active_mod)
        try:
            response = await call_next(request)
            logger.info(f"FastAPI Response: {response.status_code}")
            return response
        finally:
            reset_request_active_mod_id(am_token)

    @app.middleware("http")
    async def vue_dist_no_store_cache(request: Request, call_next):
        """桌面/Electron 易缓存旧版 index-*.js；对 SPA 与 /assets 禁用强缓存。"""
        response = await call_next(request)
        path = request.url.path or ""
        if path == "/" or path.endswith(".html") or path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.middleware("http")
    async def neuro_http_trace_outer(request: Request, call_next):
        """最外层 HTTP trace（最后注册 = 最先执行）。"""
        from app.middleware.neuro_http_trace import neuro_http_trace_middleware

        return await neuro_http_trace_middleware(request, call_next)


def _register_prometheus_metrics(app: FastAPI):
    """注册 Prometheus 监控端点"""
    try:
        from fastapi.responses import Response
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        @app.get("/metrics")
        async def metrics_endpoint():
            """
            Prometheus 指标导出端点

            返回 Prometheus 格式的监控指标
            """
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST,
            )

        logger.info("✅ Prometheus 监控端点已注册 (/metrics)")
    except ImportError:
        logger.warning("⚠️ prometheus_client 未安装，监控端点不可用")
    except Exception as e:
        logger.warning(f"⚠️ Prometheus 监控端点注册失败：{e}")


# 兼容性函数，用于从现有代码调用
def get_fastapi_app() -> FastAPI:
    """获取 FastAPI 应用实例（单例模式）"""
    if not hasattr(get_fastapi_app, "_app"):
        get_fastapi_app._app = create_fastapi_app()
    return get_fastapi_app._app
