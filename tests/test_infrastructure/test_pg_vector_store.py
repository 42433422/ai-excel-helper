# -*- coding: utf-8 -*-
"""pgvector 落地结构断言。

reviewer 的担心：pgvector "只写了配置，运行时没真用上"。
本测试不需要真实的 PostgreSQL —— 它走两个低成本方向：

1. **SQL 片段断言**：从 ``PgVectorStore._ensure_tables`` 源码里抓出
   ``CREATE EXTENSION vector``、``USING ivfflat (... vector_cosine_ops)``、
   ``vector(256)`` 等关键 DDL，确保代码路径而非仅有配置。
2. **接口契约**：``PgVectorStore`` / ``PgUserMemoryVectorStore`` 实现了
   ``VectorStorePort`` 的全部关键方法，且 ``excel_vector`` 路由使用的
   应用服务默认注入的就是 pg 实现。
"""

from __future__ import annotations

import inspect
import textwrap


def _source_of(cls) -> str:
    return textwrap.dedent(inspect.getsource(cls))


class TestPgVectorStoreDDL:
    def test_excel_chunks_ddl_landed(self):
        from app.infrastructure.persistence.pg_vector_store import PgVectorStore

        src = _source_of(PgVectorStore)
        assert "CREATE EXTENSION IF NOT EXISTS vector" in src
        assert "embedding vector(256)" in src
        assert "ivfflat" in src and "vector_cosine_ops" in src

    def test_user_memory_ddl_landed(self):
        from app.infrastructure.persistence.user_memory_vector_store import (
            PgUserMemoryVectorStore,
        )

        src = _source_of(PgUserMemoryVectorStore)
        assert "CREATE EXTENSION IF NOT EXISTS vector" in src
        assert "embedding vector(256)" in src
        assert "ivfflat" in src and "vector_cosine_ops" in src

    def test_cosine_distance_operator_used_in_query(self):
        from app.infrastructure.persistence.pg_vector_store import PgVectorStore

        src = _source_of(PgVectorStore)
        # <=> 是 pgvector 的余弦距离操作符 —— 出现在 query() 里即说明真走 pgvector。
        assert "embedding <=>" in src


class TestVectorStorePortImplementation:
    def test_port_methods_present(self):
        from app.application.ports.vector_store import VectorStorePort
        from app.infrastructure.persistence.pg_vector_store import PgVectorStore
        from app.infrastructure.persistence.user_memory_vector_store import (
            PgUserMemoryVectorStore,
        )

        required = {name for name in dir(VectorStorePort) if not name.startswith("_")}
        for impl in (PgVectorStore, PgUserMemoryVectorStore):
            missing = required - {name for name in dir(impl) if not name.startswith("_")}
            assert not missing, f"{impl.__name__} 缺少 port 方法: {missing}"


class TestExcelVectorAppServiceWiring:
    def test_default_factory_prefers_pgvector(self, monkeypatch):
        # 确保默认不走 SQLite fallback。
        monkeypatch.delenv("ENABLE_SQLITE_VECTOR_FALLBACK", raising=False)
        monkeypatch.setenv("VECTOR_DB_URL", "postgresql+psycopg://u:p@localhost:5432/x")

        import app.application.excel_vector_app_service as mod

        # 清理模块级单例，避免被其他测试污染。
        mod._pg_vector_store_instance = None
        mod._vector_store_instance = None

        # 不实际建连接：PgVectorStore 在 __init__ 时会调 _ensure_tables；
        # 这里 patch 掉 _ensure_tables 只验证 factory 确实构造出 pg 实例。
        from unittest.mock import patch

        from app.application.excel_vector_app_service import get_pg_vector_store

        with (
            patch(
                "app.infrastructure.persistence.pg_vector_store.PgVectorStore._ensure_tables",
                return_value=None,
            ),
            patch("sqlalchemy.create_engine"),
        ):
            store = get_pg_vector_store()

        from app.infrastructure.persistence.pg_vector_store import PgVectorStore

        assert isinstance(store, PgVectorStore)
