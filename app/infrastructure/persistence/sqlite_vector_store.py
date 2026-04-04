from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional

import numpy as np

from app.application.ports.vector_store import VectorStorePort
from app.utils.external_sqlite import connect_sqlite

logger = logging.getLogger(__name__)


class SQLiteVectorStore(VectorStorePort):
    """基于 SQLite + Python 相似度计算的轻量向量存储。"""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_tables()

    def _get_conn(self):
        conn = connect_sqlite(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS excel_vector_indexes (
                    index_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS excel_vector_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    index_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(index_id) REFERENCES excel_vector_indexes(index_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_excel_vector_chunks_index_id ON excel_vector_chunks(index_id)"
            )
            conn.commit()

    def create_or_update_index(
        self,
        index_id: str,
        name: str,
        source_file: str,
    ) -> None:
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO excel_vector_indexes(index_id, name, source_file, created_at, updated_at, chunk_count)
                VALUES(?, ?, ?, ?, ?, 0)
                ON CONFLICT(index_id) DO UPDATE SET
                    name=excluded.name,
                    source_file=excluded.source_file,
                    updated_at=excluded.updated_at
                """,
                (index_id, name, source_file, now, now),
            )
            conn.commit()

    def upsert_chunks(self, index_id: str, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0

        now = time.time()
        with self._get_conn() as conn:
            conn.execute("DELETE FROM excel_vector_chunks WHERE index_id = ?", (index_id,))
            for chunk in chunks:
                conn.execute(
                    """
                    INSERT INTO excel_vector_chunks(chunk_id, index_id, content, embedding, metadata, created_at)
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk["chunk_id"],
                        index_id,
                        chunk["content"],
                        json.dumps(chunk["embedding"], ensure_ascii=False),
                        json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                        now,
                    ),
                )
            conn.execute(
                """
                UPDATE excel_vector_indexes
                SET chunk_count = ?, updated_at = ?
                WHERE index_id = ?
                """,
                (len(chunks), now, index_id),
            )
            conn.commit()
        return len(chunks)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
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
        del filters  # 预留接口，当前轻量实现不做 DB 侧过滤
        query_arr = np.array(query_vector, dtype=np.float32)
        rows: List[sqlite3.Row] = []
        with self._get_conn() as conn:
            result = conn.execute(
                "SELECT chunk_id, content, embedding, metadata FROM excel_vector_chunks WHERE index_id = ?",
                (index_id,),
            )
            rows = result.fetchall()

        scored: List[Dict[str, Any]] = []
        for row in rows:
            try:
                emb = np.array(json.loads(row["embedding"]), dtype=np.float32)
                score = self._cosine_similarity(query_arr, emb)
                scored.append(
                    {
                        "chunk_id": row["chunk_id"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"] or "{}"),
                        "score": score,
                    }
                )
            except Exception:
                continue

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: max(top_k, 1)]

    def list_indexes(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            result = conn.execute(
                """
                SELECT index_id, name, source_file, created_at, updated_at, chunk_count
                FROM excel_vector_indexes
                ORDER BY updated_at DESC
                """
            )
            rows = result.fetchall()
        return [dict(row) for row in rows]

    def delete_index(self, index_id: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM excel_vector_chunks WHERE index_id = ?", (index_id,))
            result = conn.execute("DELETE FROM excel_vector_indexes WHERE index_id = ?", (index_id,))
            conn.commit()
        return result.rowcount > 0
