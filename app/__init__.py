"""
Flask 应用工厂模块

提供 create_app() 函数，用于创建和配置 Flask 应用实例。
"""

import os
import logging
from flask import Flask, send_from_directory
from flask_cors import CORS
from flasgger import Swagger

from .config import Config, get_config
from .extensions import init_extensions

# 导入数据库初始化函数（使用 XCAGI 项目的 db.py）
# 技术债 #001 已解决：不再依赖 AI 助手/db.py
from db import initialize_databases, init_wechat_tasks_table

# 获取应用基础目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(config_object: type[Config] | None = None) -> Flask:
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
    swagger = Swagger(app, template={
        'title': 'XCAGI API Documentation',
        'description': 'XCAGI 系统 API 接口文档',
        'version': '1.0.0'
    })
    
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
    register_blueprints(app)
    
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
        # 其他路径直接返回文件
        file_path = os.path.join(BASE_DIR, 'templates', 'vue-dist', path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(os.path.join(BASE_DIR, 'templates', 'vue-dist'), path)
        return {"success": False, "message": "未找到资源"}, 404
    
    logger.info("Flask 应用创建完成")
    return app
