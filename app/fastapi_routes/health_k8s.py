"""K8s 风格健康检查（自归档 health 蓝图迁移，路径保持 /health/*）。"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from typing import Any

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health-k8s"])


def _check_database() -> dict[str, Any]:
    try:
        from app.db.session import get_db

        with get_db() as db:
            db.execute(text("SELECT 1"))
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_redis() -> dict[str, Any]:
    try:
        import redis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(redis_url)
        client.ping()
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_ai_service() -> dict[str, Any]:
    """统一意图识别引擎探针。

    历史版本直接 ``recognizer.is_ready()``，而 ``UnifiedIntentRecognizer``
    最初并未定义该方法。此处改为鸭子类型调用，并回退到 ``load()``。
    """

    try:
        from app.domain.services.unified_intent_recognizer import (
            get_unified_intent_recognizer,
        )

        recognizer = get_unified_intent_recognizer()
        ready = False
        if hasattr(recognizer, "is_ready"):
            ready = bool(recognizer.is_ready())
        else:
            ready = bool(recognizer.load())

        engines: dict[str, Any] = {}
        getter = getattr(recognizer, "get_engine_status", None)
        if callable(getter):
            try:
                engines = getter()
            except Exception as exc:  # pragma: no cover - diagnostic only
                engines = {"error": str(exc)}

        return {
            "status": "healthy" if ready else "degraded",
            "model_loaded": ready,
            "engines": engines,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_pgvector() -> dict[str, Any]:
    """pgvector 深度探针：不仅 ping 库，还会校验扩展可用 + 诊断索引。"""

    try:
        from sqlalchemy import create_engine

        db_url = (os.environ.get("VECTOR_DB_URL") or os.environ.get("DATABASE_URL") or "").strip()
        if not db_url:
            return {"status": "disabled", "reason": "no_vector_db_url"}

        if "postgres" not in db_url.lower():
            # SQLite fallback 不走 pgvector，视为 ``disabled`` 但不致命。
            return {
                "status": "disabled",
                "reason": "not_postgres",
                "dialect": db_url.split("://", 1)[0],
            }

        engine = create_engine(db_url, pool_pre_ping=True, echo=False)
        with engine.connect() as conn:
            ext_row = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).first()

            if not ext_row:
                return {
                    "status": "unhealthy",
                    "error": "pgvector extension not installed",
                    "hint": "CREATE EXTENSION vector; (需要 superuser)",
                }

            index_count = (
                conn.execute(
                    text("SELECT COUNT(*) FROM pg_indexes WHERE indexdef ILIKE '%ivfflat%'")
                ).scalar()
                or 0
            )

            chunk_tables = conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.columns
                    WHERE udt_name = 'vector'
                    ORDER BY table_name
                    """
                )
            ).fetchall()
            tables = sorted({row[0] for row in chunk_tables})

        engine.dispose()

        return {
            "status": "healthy",
            "extension_version": ext_row[0],
            "ivfflat_index_count": int(index_count),
            "vector_tables": tables,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_rasa_nlu() -> dict[str, Any]:
    try:
        from app.ai_engines.rasa.nlu_service import get_rasa_nlu_service

        svc = get_rasa_nlu_service()
        snapshot = svc.get_status() if hasattr(svc, "get_status") else {}
        available = bool(getattr(svc, "is_available", lambda: False)())
        if not snapshot.get("enabled", True):
            return {"status": "disabled", "detail": snapshot}
        return {
            "status": "healthy" if available else "degraded",
            "available": available,
            "detail": snapshot,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _system_info() -> dict[str, Any]:
    root = "C:\\" if os.name == "nt" else "/"
    try:
        disk = psutil.disk_usage(root).percent
    except Exception:
        disk = 0.0
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
        "disk_percent": disk,
    }


@router.get("/health/liveness")
def liveness():
    return JSONResponse(
        {
            "status": "alive",
            "timestamp": datetime.now(UTC).isoformat(),
            "python_version": sys.version,
        }
    )


_ACCEPTABLE = {"healthy", "disabled"}


@router.get("/health/readiness")
def readiness():
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "ai_service": _check_ai_service(),
        "pgvector": _check_pgvector(),
        "rasa": _check_rasa_nlu(),
    }
    all_healthy = all(c["status"] in _ACCEPTABLE for c in checks.values())
    payload = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }
    return JSONResponse(payload, status_code=200 if all_healthy else 503)


@router.get("/health/details")
def health_details():
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "ai_service": _check_ai_service(),
        "pgvector": _check_pgvector(),
        "rasa": _check_rasa_nlu(),
    }
    ok = all(c["status"] in _ACCEPTABLE for c in checks.values())
    return JSONResponse(
        {
            "status": "healthy" if ok else "degraded",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "3.0.0",
            "checks": checks,
            "system": _system_info(),
        }
    )


@router.get("/api/diagnostics/capabilities")
def capabilities_diagnostics():
    """能力落地自检清单。

    专门用于回答"RASA / pgvector 真的跑起来了吗？"类审查问题：

    - ``rasa``: 加载模式、模型路径、是否可用、阈值。
    - ``pgvector``: 扩展版本、ivfflat 索引数、挂载的向量表。
    - ``intent_engines``: 每个子识别器（rule / distilled / bert / deepseek / rasa）
      是否真正被 ``UnifiedIntentRecognizer`` 接管。

    允许在 ``/health/readiness`` 内被聚合；这里额外暴露出来是为了方便
    CI / 灰度前人工执行一次：

    .. code-block:: bash

        curl -s http://127.0.0.1:5000/api/diagnostics/capabilities | jq
    """

    rasa_check = _check_rasa_nlu()
    pgvector_check = _check_pgvector()
    ai_check = _check_ai_service()

    # intent_engines 单独取一份快照，便于前端渲染"哪些引擎已落地"。
    intent_engines: dict[str, Any] = {}
    try:
        from app.domain.services.unified_intent_recognizer import (
            get_unified_intent_recognizer,
        )

        recognizer = get_unified_intent_recognizer()
        getter = getattr(recognizer, "get_engine_status", None)
        if callable(getter):
            intent_engines = getter()
    except Exception as exc:  # pragma: no cover - diagnostic only
        intent_engines = {"error": str(exc)}

    return JSONResponse(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "rasa": rasa_check,
            "pgvector": pgvector_check,
            "intent_engines": intent_engines,
            "ai_service": ai_check,
        }
    )
