"""
Flask 扩展集中管理模块

在此模块中定义所有 Flask 扩展实例，通过 init_app() 方法延迟初始化。
"""

from flask_caching import Cache
from celery import Celery

# 全局扩展实例
# 这些实例在模块级别创建，但需要在使用前通过 init_app() 初始化

cache = Cache(config={"CACHE_TYPE": "RedisCache"})
"""
Flask-Caching 实例

使用方式：
    cache.init_app(app)
"""

celery_app = Celery(__name__)
"""
Celery 应用实例

使用方式：
    celery_app.conf.update(app.config.get("CELERY", {}))
"""


def init_cache(app, config=None):
    """
    初始化缓存扩展
    
    Args:
        app: Flask 应用实例
        config: 可选的缓存配置字典
    
    Returns:
        初始化后的 cache 实例
    """
    if config:
        cache.init_app(app, config=config)
    else:
        cache.init_app(app)
    return cache


def init_celery(app):
    """
    初始化 Celery 扩展
    
    Args:
        app: Flask 应用实例
    
    Returns:
        初始化后的 celery_app 实例
    """
    celery_config = app.config.get("CELERY", {})
    celery_app.conf.update(celery_config)
    
    # 如果有自定义 Celery 配置，可以在这里添加
    # 例如：celery_app.autodiscover_tasks(['app.tasks'])
    
    return celery_app


def init_extensions(app):
    """
    一次性初始化所有扩展
    
    Args:
        app: Flask 应用实例
    """
    init_cache(app)
    init_celery(app)
