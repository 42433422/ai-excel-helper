import logging
import os

logger = logging.getLogger(__name__)

# 仓库根目录：本文件位于 ``app/config.py``，故此处为上一级目录（含 ``app/``、``backend/``、``XCAGI/`` 的一体化仓库根）。
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 本地开发：加载仓库根目录 ``.env``。与 ``XCAGI/run_fastapi.py`` 先加载的 ``XCAGI/.env`` 并存时，python-dotenv 默认不覆盖已有环境变量，故先执行的启动脚本里的变量优先生效。
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(BASE_DIR, ".env"))
    # 与 XCAGI/run_fastapi.py 一致：热重载子进程只 import app，不会执行 run_fastapi.main()
    _xcagi_env = os.path.join(BASE_DIR, "XCAGI", ".env")
    if os.path.isfile(_xcagi_env):
        load_dotenv(_xcagi_env, override=False)
except ImportError:
    pass

try:
    from app.desktop_runtime import configure_desktop_environment, is_desktop_mode

    if is_desktop_mode():
        configure_desktop_environment(os.environ.get("XCAGI_DATA_DIR"))
except Exception:
    # Config import must stay side-effect tolerant for tests and management scripts.
    pass


class Config:
    """基础配置类"""

    # 安全密钥：优先使用环境变量，开发环境允许临时随机值。
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # 调试模式
    DEBUG = os.environ.get("XCAGI_DEBUG", "1") == "1"

    DESKTOP_MODE = os.environ.get("XCAGI_DESKTOP_MODE", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # Redis / Cache 配置
    CACHE_REDIS_URL = os.environ.get(
        "CACHE_REDIS_URL",
        "" if DESKTOP_MODE else "redis://localhost:6379/0",
    )

    # Celery 配置
    CELERY = {
        "broker_url": os.environ.get(
            "CELERY_BROKER_URL",
            "memory://" if DESKTOP_MODE else "redis://localhost:6379/1",
        ),
        "result_backend": os.environ.get(
            "CELERY_RESULT_BACKEND",
            "cache+memory://" if DESKTOP_MODE else "redis://localhost:6379/2",
        ),
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
    SESSION_COOKIE_MAX_AGE = int(os.environ.get("SESSION_COOKIE_MAX_AGE", "315360000"))

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
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32).hex()

    # 可选环境变量（不设则保持原行为）：
    # XCAGI_SKIP_INTENT_LLM=1 — 在「非 pro source」的 chat 路径上跳过 HybridIntent 内的 DeepSeek 意图，
    #   仅用规则意图 + 后续主对话一次 DeepSeek（减轻短时多路连接失败；/api/ai/chat 固定 source=pro 时走 unified，不受此项影响）。
    # XCAGI_NEURO_INTENT=0 — 关闭 NeuroBus 启动与意图桥接（反射弧 + intent 域事件）；默认开启。
    # XCAGI_NEURO_HTTP_TRACE=1 — 开启 HTTP 层 Neuro 事件（配合 XCAGI_NEURO_HTTP_SAMPLE 采样率 0~1）。
    # XCAGI_NEURO_HTTP_BODY_MAX — body 预览最大字节；默认 0 不记录 body。
    # XCAGI_NEURO_APP_SAMPLE — Application/Services 自动包装采样率，默认 1.0；高频环境可降至 0.05。
    # XCAGI_NEURO_SERVICE_TRACE=0 — 关闭 Services 层 service.module.trace。
    # XCAGI_NEURO_DOMAIN_METRICS=1 — IntentNeuroDomain 等 handler 计数并入 get_stats。

    # 开发环境使用不同的 Redis 数据库；桌面模式不要求 Redis。
    CACHE_REDIS_URL = os.environ.get(
        "CACHE_REDIS_URL",
        "" if Config.DESKTOP_MODE else "redis://localhost:6379/1",
    )
    CELERY = {
        **Config.CELERY,
        "broker_url": os.environ.get(
            "CELERY_BROKER_URL",
            "memory://" if Config.DESKTOP_MODE else "redis://localhost:6379/3",
        ),
        "result_backend": os.environ.get(
            "CELERY_RESULT_BACKEND",
            "cache+memory://" if Config.DESKTOP_MODE else "redis://localhost:6379/4",
        ),
    }


def _validate_production_secrets():
    secret_key = os.environ.get("SECRET_KEY", "")
    if not secret_key:
        if not Config.DEBUG:
            raise RuntimeError("SECRET_KEY is not set. Set the SECRET_KEY environment variable.")
        logger.warning("SECRET_KEY is not set. This is insecure for production.")
    elif len(secret_key) < 32:
        if not Config.DEBUG:
            raise RuntimeError(
                "SECRET_KEY is too short (minimum 32 characters). Use a strong, randomly generated key."
            )
        logger.warning("SECRET_KEY is shorter than 32 characters. This is insecure for production.")


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG = False

    @classmethod
    def init_app(cls):
        """生产环境初始化检查"""
        _validate_production_secrets()
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
