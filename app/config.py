import os

# 获取项目根目录（XCAGI 目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    """基础配置类"""
    
    # 安全密钥
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    
    # 调试模式
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
    
    # Redis / Cache 配置
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/0")
    
    # Celery 配置
    CELERY = {
        "broker_url": os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
        "result_backend": os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "Asia/Shanghai",
        "enable_utc": False,
    }
    
    # 数据库配置
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "data"))
    
    # 上传文件配置
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 日志配置
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class DevelopmentConfig(Config):
    """开发环境配置"""
    
    DEBUG = True
    
    # 开发环境使用不同的 Redis 数据库
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/1")
    CELERY = {
        **Config.CELERY,
        "broker_url": os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/3"),
        "result_backend": os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/4"),
    }


class ProductionConfig(Config):
    """生产环境配置"""
    
    DEBUG = False
    
    @classmethod
    def init_app(cls):
        """生产环境初始化检查"""
        secret_key = os.environ.get("SECRET_KEY")
        if not secret_key:
            raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
        cls.SECRET_KEY = secret_key


class TestingConfig(Config):
    """测试环境配置"""
    
    DEBUG = True
    TESTING = True
    
    # 测试环境使用内存缓存
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300


# 配置映射
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name: str = "default"):
    """根据配置名称获取配置类"""
    return config_map.get(config_name, DevelopmentConfig)
