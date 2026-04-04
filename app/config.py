import os

# 获取项目根目录（XCAGI 目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 本地开发：自动加载项目根目录 .env，无需在系统/IDE 里逐个配环境变量（未安装 python-dotenv 则静默跳过）
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass


class Config:
    """基础配置类"""

    # 安全密钥：优先使用环境变量，开发环境允许临时随机值。
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32).hex()
    
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
    
    # 数据库配置（主库默认 PostgreSQL，可通过环境变量覆盖）
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://xcagi:xcagi@localhost:5432/xcagi",
    )
    # 向量库默认与主库相同；如需拆分可单独设置。
    VECTOR_DB_URL = os.environ.get("VECTOR_DB_URL", DATABASE_URL)
    # 兼容字段：保留 SQLite 场景
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "data"))
    
    # 上传文件配置
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # Excel 向量化配置（本地轻量）
    EXCEL_VECTOR_DB_PATH = os.environ.get(
        "EXCEL_VECTOR_DB_PATH",
        os.path.join(BASE_DIR, "data", "excel_vectors.db"),
    )
    EXCEL_VECTOR_TOP_K = int(os.environ.get("EXCEL_VECTOR_TOP_K", "5"))
    EXCEL_VECTOR_CHUNK_WINDOW = int(os.environ.get("EXCEL_VECTOR_CHUNK_WINDOW", "20"))

    # Session/Cookie 安全配置
    SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "session_id")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_MAX_AGE = int(os.environ.get("SESSION_COOKIE_MAX_AGE", "86400"))

    # CORS：生产环境建议通过环境变量显式配置允许来源
    # 微信小程序需配置合法域名，在微信公众平台设置 request 合法域名
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000,"
        "http://localhost:5001,http://127.0.0.1:5001,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://*.qq.com,https://*.wechat.com",  # 微信小程序相关域名
    )
    
    # 日志配置
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class DevelopmentConfig(Config):
    """开发环境配置"""
    
    DEBUG = True

    # 可选环境变量（不设则保持原行为）：
    # XCAGI_SKIP_INTENT_LLM=1 — 在「非 pro source」的 chat 路径上跳过 HybridIntent 内的 DeepSeek 意图，
    #   仅用规则意图 + 后续主对话一次 DeepSeek（减轻短时多路连接失败；/api/ai/chat 固定 source=pro 时走 unified，不受此项影响）。
    
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
