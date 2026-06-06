# -*- coding: utf-8 -*-
"""能力落地自检脚本（RASA + pgvector）。

对应评审意见："能力（如 RASA、pgvector）仅停留在配置阶段，未看到深度落地证据。"

运行方式::

    python scripts/dev/smoke_capabilities.py

脚本会按顺序做三件事：

1. 导入并实例化 ``RasaNLUService``，打印真实状态（启用与否、模式、
   模型路径、诊断错误）。
2. 通过 ``UnifiedIntentRecognizer.get_engine_status()`` 查看每个子引擎
   是否被实际接入。
3. 检查 ``VECTOR_DB_URL`` 下 pgvector 扩展与 ivfflat 索引是否到位
   （Postgres 不可达时打印降级原因，而不是静默通过）。

脚本退出码：全部关键能力"可接受"时返回 0，否则返回 1。

"可接受" 的口径与 ``/health/readiness`` 保持一致：``healthy`` 或
``disabled``（明确关闭）都算通过；``unhealthy`` / ``degraded`` 会让脚本
非零退出，便于接入 CI。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


_ACCEPTABLE = {"healthy", "disabled"}


def _print_section(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _probe_rasa() -> dict:
    from app.ai_engines.rasa.nlu_service import RasaNLUService

    svc = RasaNLUService()
    status = svc.get_status()
    available = svc.is_available()
    sample = svc.parse("生成发货单")
    return {
        "status": "healthy" if available else ("disabled" if not status["enabled"] else "degraded"),
        "available": available,
        "detail": status,
        "sample_parse": sample,
    }


def _probe_intent_engines() -> dict:
    from app.domain.services.unified_intent_recognizer import (
        get_unified_intent_recognizer,
    )

    recognizer = get_unified_intent_recognizer()
    if hasattr(recognizer, "get_engine_status"):
        return recognizer.get_engine_status()
    return {"error": "UnifiedIntentRecognizer.get_engine_status() 未实现"}


def _probe_pgvector() -> dict:
    from sqlalchemy import create_engine, text

    db_url = (os.environ.get("VECTOR_DB_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if not db_url:
        return {"status": "disabled", "reason": "no_vector_db_url"}
    if "postgres" not in db_url.lower():
        return {
            "status": "disabled",
            "reason": "not_postgres",
            "dialect": db_url.split("://", 1)[0],
        }

    try:
        engine = create_engine(db_url, pool_pre_ping=True, echo=False)
        with engine.connect() as conn:
            ext_row = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).first()
            if not ext_row:
                return {"status": "unhealthy", "error": "vector extension missing"}
            idx = (
                conn.execute(
                    text("SELECT COUNT(*) FROM pg_indexes WHERE indexdef ILIKE '%ivfflat%'")
                ).scalar()
                or 0
            )
            tables = [
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT DISTINCT table_name FROM information_schema.columns "
                        "WHERE udt_name = 'vector' ORDER BY table_name"
                    )
                ).fetchall()
            ]
        engine.dispose()
        return {
            "status": "healthy",
            "extension_version": ext_row[0],
            "ivfflat_index_count": int(idx),
            "vector_tables": tables,
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


def main() -> int:
    report: dict = {}

    _print_section("RASA NLU")
    rasa = _probe_rasa()
    report["rasa"] = rasa
    print(json.dumps(rasa, ensure_ascii=False, indent=2, default=str))

    _print_section("Intent engines wiring (UnifiedIntentRecognizer)")
    engines = _probe_intent_engines()
    report["intent_engines"] = engines
    print(json.dumps(engines, ensure_ascii=False, indent=2, default=str))

    _print_section("pgvector")
    pg = _probe_pgvector()
    report["pgvector"] = pg
    print(json.dumps(pg, ensure_ascii=False, indent=2, default=str))

    _print_section("summary")
    overall_ok = rasa["status"] in _ACCEPTABLE and pg["status"] in _ACCEPTABLE
    print(
        json.dumps(
            {"ok": overall_ok, "rasa": rasa["status"], "pgvector": pg["status"]}, ensure_ascii=False
        )
    )

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
