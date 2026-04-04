# -*- coding: utf-8 -*-
"""
XCAGI 打包版本配置文件

使用 SQLite 数据库，无需外部 PostgreSQL 服务
"""

import os
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PackedConfig:
    """打包版本配置 - 使用 SQLite"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "xcagi_packed_secret_key_do_not_modify"

    DEBUG = False

    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'data', 'xcagi.db')}",
    )
    VECTOR_DB_URL = DATABASE_URL
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "data"))

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    EXCEL_VECTOR_DB_PATH = os.environ.get(
        "EXCEL_VECTOR_DB_PATH",
        os.path.join(BASE_DIR, "data", "excel_vectors.db"),
    )
    EXCEL_VECTOR_TOP_K = 5
    EXCEL_VECTOR_CHUNK_WINDOW = 20

    SESSION_COOKIE_NAME = "session_id"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_MAX_AGE = 86400

    CORS_ORIGINS = "*"

    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def init_app(cls):
        pass


config_map = {
    "packed": PackedConfig,
}

def get_config(config_name: str = "packed"):
    return config_map.get(config_name, PackedConfig)
