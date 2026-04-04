from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.application.ports.vector_store import VectorStorePort
from app.utils.external_sqlite import connect_sqlite
from app.utils.path_utils import get_app_data_dir

logger = logging.getLogger(__name__)


_USER_MEMORY_VECTOR_DIM = 256


class PgUserMemoryVectorStore(VectorStorePort):
    """用户记忆向量存储（Postgres + pgvector）。

    表结构：
    - user_memory_vector_indexes
    - user_memory_vector_chunks
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine: Engine = create_engine(database_url, pool_pre_ping=True, echo=False)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS user_memory_vector_indexes (
                        index_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL,
                        updated_at DOUBLE PRECISION NOT NULL,
                        chunk_count INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS user_memory_vector_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        index_id TEXT NOT NULL REFERENCES user_memory_vector_indexes(index_id) ON DELETE CASCADE,
                        content TEXT NOT NULL,
                        embedding vector(256) NOT NULL,
                        metadata JSONB NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_user_memory_vector_chunks_index_id ON user_memory_vector_chunks(index_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_user_memory_vector_chunks_embedding ON user_memory_vector_chunks USING ivfflat (embedding vector_cosine_ops)"
                )
            )

    def create_or_update_index(self, index_id: str, user_id: str) -> None:
        now = time.time()
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO user_memory_vector_indexes(index_id, user_id, created_at, updated_at, chunk_count)
                    VALUES(:index_id, :user_id, :created_at, :updated_at, 0)
                    ON CONFLICT(index_id) DO UPDATE
                    SET user_id = EXCLUDED.user_id,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {"index_id": index_id, "user_id": user_id, "created_at": now, "updated_at": now},
            )

    def upsert_chunks(self, index_id: str, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        now = time.time()
        with self._engine.begin() as conn:
            for chunk in chunks:
                conn.execute(
                    text(
                        """
                        INSERT INTO user_memory_vector_chunks(chunk_id, index_id, content, embedding, metadata, created_at)
                        VALUES(
                            :chunk_id,
                            :index_id,
                            :content,
                            CAST(:embedding AS vector),
                            CAST(:metadata AS jsonb),
                            :created_at
                        )
                        ON CONFLICT(chunk_id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            created_at = EXCLUDED.created_at,
                            index_id = EXCLUDED.index_id
                        """
                    ),
                    {
                        "chunk_id": str(chunk["chunk_id"]),
                        "index_id": index_id,
                        "content": str(chunk["content"]),
                        "embedding": json.dumps(chunk["embedding"], ensure_ascii=False),
                        "metadata": json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                        "created_at": now,
                    },
                )

            conn.execute(
                text(
                    """
                    UPDATE user_memory_vector_indexes
                    SET chunk_count = (
                        SELECT COUNT(*) FROM user_memory_vector_chunks WHERE index_id = :index_id
                    ),
                    updated_at = :updated_at
                    WHERE index_id = :index_id
                    """
                ),
                {"updated_at": now, "index_id": index_id},
            )

        return len(chunks)

    def query(
        self,
        index_id: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        del filters  # 预留接口
        with self._engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT
                        chunk_id,
                        content,
                        metadata,
                        1 - (embedding <=> CAST(:query_vector AS vector)) AS score
                    FROM user_memory_vector_chunks
                    WHERE index_id = :index_id
                    ORDER BY embedding <=> CAST(:query_vector AS vector)
                    LIMIT :top_k
                    """
                ),
                {
                    "index_id": index_id,
                    "query_vector": json.dumps(query_vector, ensure_ascii=False),
                    "top_k": max(int(top_k), 1),
                },
            ).mappings().all()

        return [
            {
                "chunk_id": row["chunk_id"],
                "content": row["content"],
                "metadata": row["metadata"] or {},
                "score": float(row["score"] or 0.0),
            }
            for row in rows
        ]

    def list_indexes(self) -> List[Dict[str, Any]]:
        with self._engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT index_id, user_id, created_at, updated_at, chunk_count
                    FROM user_memory_vector_indexes
                    ORDER BY updated_at DESC
                    """
                )
            ).mappings().all()
        return [dict(row) for row in rows]

    def delete_index(self, index_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM user_memory_vector_indexes WHERE index_id = :index_id"), {"index_id": index_id}
            )
        return bool(getattr(result, "rowcount", 0) > 0)


class SQLiteUserMemoryVectorStore(VectorStorePort):
    """用户记忆向量存储（SQLite + Python 相似度计算）。"""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_tables()

    def _get_conn(self):
        conn = connect_sqlite(self._db_path)
        # SQLite 默认不开启外键约束；不启用会导致 ON DELETE CASCADE 无效。
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        conn.row_factory = None
        return conn

    def _ensure_tables(self) -> None:
        with connect_sqlite(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memory_vector_indexes (
                    index_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memory_vector_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    index_id TEXT NOT NULL REFERENCES user_memory_vector_indexes(index_id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_memory_vector_chunks_index_id ON user_memory_vector_chunks(index_id)"
            )
            conn.commit()

    def create_or_update_index(self, index_id: str, user_id: str) -> None:
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO user_memory_vector_indexes(index_id, user_id, created_at, updated_at, chunk_count)
                VALUES(?, ?, ?, ?, 0)
                ON CONFLICT(index_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    updated_at = excluded.updated_at
                """,
                (index_id, user_id, now, now),
            )
            conn.commit()

    def upsert_chunks(self, index_id: str, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        now = time.time()
        with self._get_conn() as conn:
            for chunk in chunks:
                conn.execute(
                    """
                    INSERT INTO user_memory_vector_chunks(chunk_id, index_id, content, embedding, metadata, created_at)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id) DO UPDATE SET
                        index_id = excluded.index_id,
                        content = excluded.content,
                        embedding = excluded.embedding,
                        metadata = excluded.metadata,
                        created_at = excluded.created_at
                    """,
                    (
                        str(chunk["chunk_id"]),
                        index_id,
                        str(chunk["content"]),
                        json.dumps(chunk["embedding"], ensure_ascii=False),
                        json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                        now,
                    ),
                )

            conn.execute(
                """
                UPDATE user_memory_vector_indexes
                SET chunk_count = (
                    SELECT COUNT(*) FROM user_memory_vector_chunks WHERE index_id = ?
                ),
                updated_at = ?
                WHERE index_id = ?
                """,
                (index_id, now, index_id),
            )
            conn.commit()
        return len(chunks)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denominator == 0.0:
            return 0.0
        return float(np.dot(a, b) / denominator)

    def query(
        self,
        index_id: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        del filters
        query_arr = np.array(query_vector, dtype=np.float32)
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT chunk_id, content, embedding, metadata FROM user_memory_vector_chunks WHERE index_id = ?",
                (index_id,),
            ).fetchall()

        scored: List[Dict[str, Any]] = []
        for chunk_id, content, embedding_text, metadata_text in rows:
            try:
                emb = np.array(json.loads(embedding_text), dtype=np.float32)
                score = self._cosine_similarity(query_arr, emb)
                scored.append(
                    {
                        "chunk_id": chunk_id,
                        "content": content,
                        "metadata": json.loads(metadata_text or "{}"),
                        "score": score,
                    }
                )
            except Exception:
                continue

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: max(int(top_k), 1)]

    def list_indexes(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT index_id, user_id, created_at, updated_at, chunk_count
                FROM user_memory_vector_indexes
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [
            {"index_id": r[0], "user_id": r[1], "created_at": r[2], "updated_at": r[3], "chunk_count": r[4]}
            for r in rows
        ]

    def delete_index(self, index_id: str) -> bool:
        with self._get_conn() as conn:
            result = conn.execute("DELETE FROM user_memory_vector_indexes WHERE index_id = ?", (index_id,))
            conn.commit()
        return bool(getattr(result, "rowcount", 0) > 0)


_user_memory_sqlite_vector_store_instance: Optional[SQLiteUserMemoryVectorStore] = None
_user_memory_pg_vector_store_instance: Optional[PgUserMemoryVectorStore] = None
_user_memory_vector_store_instance: Optional[VectorStorePort] = None


def _default_user_memory_vector_db_path() -> str:
    env_path = os.environ.get("USER_MEMORY_VECTOR_DB_PATH", "").strip()
    if env_path:
        folder = os.path.dirname(env_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        return env_path
    folder = os.path.join(get_app_data_dir(), "vectors")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "user_memory_vectors.db")


def get_user_memory_sqlite_vector_store() -> SQLiteUserMemoryVectorStore:
    global _user_memory_sqlite_vector_store_instance
    if _user_memory_sqlite_vector_store_instance is None:
        _user_memory_sqlite_vector_store_instance = SQLiteUserMemoryVectorStore(db_path=_default_user_memory_vector_db_path())
    return _user_memory_sqlite_vector_store_instance


def get_user_memory_pg_vector_store() -> PgUserMemoryVectorStore:
    global _user_memory_pg_vector_store_instance
    if _user_memory_pg_vector_store_instance is None:
        db_url = os.environ.get("VECTOR_DB_URL") or os.environ.get("DATABASE_URL")
        if not db_url:
            raise ValueError("缺少 VECTOR_DB_URL / DATABASE_URL 配置")
        _user_memory_pg_vector_store_instance = PgUserMemoryVectorStore(database_url=db_url)
    return _user_memory_pg_vector_store_instance


def get_user_memory_vector_store() -> VectorStorePort:
    """获取用户记忆向量存储实例（带 SQLite fallback）。"""

    global _user_memory_vector_store_instance
    if _user_memory_vector_store_instance is not None:
        return _user_memory_vector_store_instance

    use_sqlite_fallback = (os.environ.get("ENABLE_SQLITE_VECTOR_FALLBACK", "0") or "0").strip() == "1"
    if use_sqlite_fallback:
        _user_memory_vector_store_instance = get_user_memory_sqlite_vector_store()
    else:
        _user_memory_vector_store_instance = get_user_memory_pg_vector_store()
    return _user_memory_vector_store_instance

