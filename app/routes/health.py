# -*- coding: utf-8 -*-
"""
健康检查路由

提供 Kubernetes liveness 和 readiness 探针端点。
"""

import sys
from datetime import datetime, timezone
from typing import Any, Dict

import psutil
from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


def check_database() -> Dict[str, Any]:
    """检查数据库连接"""
    try:
        from app.db.session import get_db
        with get_db() as db:
            db.execute("SELECT 1")
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_redis() -> Dict[str, Any]:
    """检查 Redis 连接"""
    try:
        import redis
        redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(redis_url)
        client.ping()
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_ai_service() -> Dict[str, Any]:
    """检查 AI 服务可用性"""
    try:
        from app.services import UnifiedIntentRecognizer
        recognizer = UnifiedIntentRecognizer()
        return {"status": "healthy", "model_loaded": recognizer.is_ready()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
        "disk_percent": psutil.disk_usage('/').percent
    }


@health_bp.route("/health/liveness", methods=["GET"])
def liveness() -> tuple:
    """
    Liveness 探针

    检查进程是否存活。
    Returns:
        200 if alive, 503 if dead
    """
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version
    }), 200


@health_bp.route("/health/readiness", methods=["GET"])
def readiness() -> tuple:
    """
    Readiness 探针

    检查应用及所有依赖是否就绪。
    Returns:
        200 if ready, 503 if not ready
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "ai_service": check_ai_service()
    }

    all_healthy = all(
        check["status"] == "healthy"
        for check in checks.values()
    )

    response_data = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }

    status_code = 200 if all_healthy else 503
    return jsonify(response_data), status_code


@health_bp.route("/health/details", methods=["GET"])
def health_details() -> tuple:
    """
    详细健康信息

    返回完整的健康状态和系统信息。
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "ai_service": check_ai_service()
    }

    return jsonify({
        "status": "healthy" if all(c["status"] == "healthy" for c in checks.values()) else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "3.0.0",
        "checks": checks,
        "system": get_system_info()
    }), 200