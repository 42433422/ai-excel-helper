"""
Flask 应用工厂模块

提供 create_app() 函数，用于创建和配置 Flask 应用实例。
"""

import logging
import os
import time
import uuid

from flask import Flask, g, request, send_from_directory
from flask_cors import CORS

try:
    from flasgger import Swagger  # type: ignore
except ModuleNotFoundError:
    Swagger = None  # type: ignore

# 导入数据库初始化函数（应用内，不依赖根目录 db.py）
from app.db.init_db import init_wechat_tasks_table, initialize_databases

from .config import Config, get_config
from .extensions import init_extensions

# 获取应用基础目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(
    config_object: type[Config] | None = None,
    blueprint_groups: list[str] | None = None,
) -> Flask:
    """
    创建并配置 Flask 应用实例
    
    Args:
        config_object: 配置类，如果为 None 则使用默认配置
        
    Returns:
        配置好的 Flask 应用实例
    """
    # 创建 Flask 应用
    app = Flask(
        __name__,
        static_folder=None,  # 禁用默认的静态文件服务，使用自定义路由
        template_folder=os.path.join(BASE_DIR, "templates"),
    )
    
    # 加载配置
    if config_object is None:
        config_object = get_config("default")
    app.config.from_object(config_object)
    
    # 配置日志
    logging.basicConfig(
        level=app.config.get("LOG_LEVEL", "INFO"),
        format=app.config.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger = logging.getLogger(__name__)
    
    # 初始化数据库
    logger.info("初始化数据库...")
    initialize_databases()
    init_wechat_tasks_table()
    
    # 初始化 Swagger 文档（必须在注册蓝图之前）
    logger.info("初始化 Swagger 文档...")
    if Swagger is not None:
        _swagger = Swagger(app, template={
            'title': 'XCAGI API Documentation',
            'description': 'XCAGI 系统 API 接口文档',
            'version': '1.0.0'
        })
    else:
        logger.warning("未安装 flasgger，Swagger 文档将被跳过。")
    
    # 配置 CORS，允许前端访问（开发环境允许所有来源）
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True
        }
    })
    
    # 初始化扩展（统一管理所有扩展）
    logger.info("初始化扩展...")
    init_extensions(app)
    
    # 注册蓝图
    logger.info("注册路由蓝图...")
    from .routes import register_blueprints
    register_blueprints(app, blueprint_groups=blueprint_groups)

    # ---------------------------------------------------------------------
    # 全局请求日志（NDJSON + 标准日志）
    # ---------------------------------------------------------------------
    from app.utils.logging_utils import debug_ndjson

    def _truncate(val: str, max_len: int = 2000) -> str:
        if not isinstance(val, str):
            val = str(val)
        return val if len(val) <= max_len else (val[:max_len] + "...<truncated>")

    @app.before_request
    def _log_request_start():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        g._start_time = time.time()

        if request.path.startswith("/api/"):
            try:
                body_preview = ""
                # 只记录 JSON / 表单的简要信息，避免记录二进制或超大内容
                if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                    if request.is_json:
                        body_preview = _truncate(request.get_data(as_text=True) or "")
                    else:
                        # form / query
                        body_preview = _truncate(str(request.form.to_dict() if request.form else {}))

                debug_ndjson({
                    "type": "http_request",
                    "phase": "start",
                    "request_id": g.request_id,
                    "method": request.method,
                    "path": request.path,
                    "query": request.query_string.decode("utf-8", "ignore"),
                    "remote_addr": request.headers.get("X-Forwarded-For") or request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "content_type": request.headers.get("Content-Type", ""),
                    "body_preview": body_preview,
                })
            except Exception:
                pass

    @app.after_request
    def _log_request_end(response):
        try:
            if not request.path.startswith("/api/"):
                return response

            elapsed_ms = int((time.time() - getattr(g, "_start_time", time.time())) * 1000)

            # 仅记录 JSON 响应的 preview（避免记录文件下载/大二进制）
            resp_preview = ""
            ct = (response.headers.get("Content-Type") or "")
            if "application/json" in ct:
                try:
                    resp_preview = _truncate(response.get_data(as_text=True) or "")
                except Exception:
                    resp_preview = ""

            debug_ndjson({
                "type": "http_request",
                "phase": "end",
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "elapsed_ms": elapsed_ms,
                "response_content_type": ct,
                "response_preview": resp_preview,
            })

            # 同时输出一条常规日志，方便你在控制台直接看
            logging.getLogger("xcagi.http").info(
                "[%s] %s %s -> %s (%sms)",
                getattr(g, "request_id", "-"),
                request.method,
                request.path,
                response.status_code,
                elapsed_ms,
            )
        except Exception:
            pass
        return response
    
    # 初始化 AI 对话服务（在蓝图注册之后，确保能正确获取配置）
    logger.info("初始化 AI 对话服务...")
    from .services.ai_conversation_service import init_ai_conversation_service
    init_ai_conversation_service()
    
    # 注册前端路由（必须在 Swagger 之后）
    @app.route('/')
    def index():
        return send_from_directory(os.path.join(BASE_DIR, 'templates', 'vue-dist'), 'index.html')
    
    # 注册静态文件服务（必须在通用路由之前）
    @app.route('/static/<path:path>')
    def serve_static(path):
        """提供静态 CSS/JS 文件"""
        # 首先尝试从 templates/vue-dist/static 查找
        file_path = os.path.join(BASE_DIR, 'templates', 'vue-dist', 'static', path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(os.path.join(BASE_DIR, 'templates', 'vue-dist', 'static'), path)
        # 如果不存在，从 static 目录查找
        file_path = os.path.join(BASE_DIR, 'static', path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(os.path.join(BASE_DIR, 'static'), path)
        return {"success": False, "message": "未找到资源"}, 404
    
    # 注册前端静态文件路由（最后注册，避免拦截其他路由）
    @app.route('/<path:path>')
    def serve_vue(path):
        # 排除 Swagger 路径和 API 路径
        if path.startswith('apidocs') or path.startswith('apispec') or path.startswith('api'):
            return {"success": False, "message": "未找到资源"}, 404
        # 处理 /static/ 路径
        if path.startswith('static/'):
            file_path = os.path.join(BASE_DIR, 'templates', 'vue-dist', path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return send_from_directory(os.path.join(BASE_DIR, 'templates', 'vue-dist'), path)
            return {"success": False, "message": "未找到资源"}, 404
        # SPA 路由：对于 Vue Router 的路径，返回 index.html
        file_path = os.path.join(BASE_DIR, 'templates', 'vue-dist', path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(os.path.join(BASE_DIR, 'templates', 'vue-dist'), path)
        # 路径不存在，返回 index.html 让 Vue Router 处理
        return send_from_directory(os.path.join(BASE_DIR, 'templates', 'vue-dist'), 'index.html')
    
    logger.info("Flask 应用创建完成")
    return app
