from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.application.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)


class PgVectorStore(VectorStorePort):
    """基于 PostgreSQL + pgvector 的向量存储实现。"""

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
                    CREATE TABLE IF NOT EXISTS excel_vector_indexes (
                        index_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        source_file TEXT NOT NULL,
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
                    CREATE TABLE IF NOT EXISTS excel_vector_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        index_id TEXT NOT NULL REFERENCES excel_vector_indexes(index_id) ON DELETE CASCADE,
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
                    "CREATE INDEX IF NOT EXISTS idx_excel_vector_chunks_index_id ON excel_vector_chunks(index_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_excel_vector_chunks_embedding ON excel_vector_chunks USING ivfflat (embedding vector_cosine_ops)"
                )
            )

    def create_or_update_index(self, index_id: str, name: str, source_file: str) -> None:
        now = time.time()
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO excel_vector_indexes(index_id, name, source_file, created_at, updated_at, chunk_count)
                    VALUES(:index_id, :name, :source_file, :created_at, :updated_at, 0)
                    ON CONFLICT(index_id) DO UPDATE
                    SET name = EXCLUDED.name,
                        source_file = EXCLUDED.source_file,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "index_id": index_id,
                    "name": name,
                    "source_file": source_file,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    def upsert_chunks(self, index_id: str, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        now = time.time()
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM excel_vector_chunks WHERE index_id = :index_id"), {"index_id": index_id})
            for chunk in chunks:
                conn.execute(
                    text(
                        """
                        INSERT INTO excel_vector_chunks(chunk_id, index_id, content, embedding, metadata, created_at)
                        VALUES(
                            :chunk_id,
                            :index_id,
                            :content,
                            CAST(:embedding AS vector),
                            CAST(:metadata AS jsonb),
                            :created_at
                        )
                        """
                    ),
                    {
                        "chunk_id": chunk["chunk_id"],
                        "index_id": index_id,
                        "content": chunk["content"],
                        "embedding": json.dumps(chunk["embedding"], ensure_ascii=False),
                        "metadata": json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                        "created_at": now,
                    },
                )
            conn.execute(
                text(
                    """
                    UPDATE excel_vector_indexes
                    SET chunk_count = :chunk_count, updated_at = :updated_at
                    WHERE index_id = :index_id
                    """
                ),
                {"chunk_count": len(chunks), "updated_at": now, "index_id": index_id},
            )
        return len(chunks)

    def query(
        self,
        index_id: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        del filters
        with self._engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT
                        chunk_id,
                        content,
                        metadata,
                        1 - (embedding <=> CAST(:query_vector AS vector)) AS score
                    FROM excel_vector_chunks
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
                    SELECT index_id, name, source_file, created_at, updated_at, chunk_count
                    FROM excel_vector_indexes
                    ORDER BY updated_at DESC
                    """
                )
            ).mappings().all()
        return [dict(row) for row in rows]

    def delete_index(self, index_id: str) -> bool:
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM excel_vector_chunks WHERE index_id = :index_id"), {"index_id": index_id})
            result = conn.execute(
                text("DELETE FROM excel_vector_indexes WHERE index_id = :index_id"),
                {"index_id": index_id},
            )
        return result.rowcount > 0
