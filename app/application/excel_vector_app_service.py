from __future__ import annotations

import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.application.ports.embedder import EmbedderPort
from app.application.ports.vector_store import VectorStorePort
from app.infrastructure.persistence.pg_vector_store import PgVectorStore
from app.infrastructure.persistence.sqlite_vector_store import SQLiteVectorStore
from app.utils.path_utils import get_app_data_dir


@dataclass
class ExcelVectorChunk:
    chunk_id: str
    content: str
    metadata: Dict[str, Any]


class HashEmbedder(EmbedderPort):
    """无需外部依赖的轻量哈希嵌入。"""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = max(64, dimensions)

    def _tokenize(self, text: str) -> List[str]:
        raw = str(text or "").strip().lower()
        if not raw:
            return []

        tokens: List[str] = []
        ascii_tokens = re.findall(r"[a-z0-9]+", raw)
        tokens.extend(ascii_tokens)

        cjk_chars = re.findall(r"[\u4e00-\u9fff]", raw)
        tokens.extend(cjk_chars)
        if len(cjk_chars) >= 2:
            tokens.extend(
                "".join(cjk_chars[i : i + 2]) for i in range(0, len(cjk_chars) - 1)
            )
        return tokens

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self._dimensions
        tokens = self._tokenize(text)
        if not tokens:
            return vec

        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self._dimensions
            sign = 1.0 if int(digest[-1], 16) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


class ExcelVectorIngestApplicationService:
    def __init__(
        self,
        vector_store: Optional[VectorStorePort] = None,
        embedder: Optional[EmbedderPort] = None,
        chunk_window_size: int = 20,
    ) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._embedder = embedder or HashEmbedder()
        self._chunk_window_size = max(5, int(chunk_window_size))

    def ingest_excel(
        self,
        file_path: str,
        index_name: Optional[str] = None,
        index_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "message": f"文件不存在: {file_path}"}

        target_index_id = index_id or uuid.uuid4().hex
        name = (index_name or path.stem or target_index_id).strip()

        sheets = pd.read_excel(file_path, sheet_name=None)
        chunks = self._build_chunks(sheets, source_file=path.name)
        if not chunks:
            return {"success": False, "message": "Excel 中没有可索引的有效数据"}

        texts = [chunk.content for chunk in chunks]
        embeddings = self._embedder.embed_texts(texts)
        store_payload: List[Dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings):
            store_payload.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "embedding": embedding,
                    "metadata": chunk.metadata,
                }
            )

        if hasattr(self._vector_store, "create_or_update_index"):
            self._vector_store.create_or_update_index(
                index_id=target_index_id,
                name=name,
                source_file=path.name,
            )

        written = self._vector_store.upsert_chunks(target_index_id, store_payload)
        return {
            "success": True,
            "index_id": target_index_id,
            "index_name": name,
            "source_file": path.name,
            "chunk_count": written,
        }

    def _build_chunks(self, sheets: Dict[str, pd.DataFrame], source_file: str) -> List[ExcelVectorChunk]:
        chunks: List[ExcelVectorChunk] = []

        for sheet_name, df in sheets.items():
            if df is None or df.empty:
                continue

            normalized = df.fillna("")
            columns = [str(col).strip() for col in normalized.columns]

            # 行级分块：对精准定位最有效
            for row_idx, (_, row) in enumerate(normalized.iterrows(), start=1):
                row_pairs = []
                for col in columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        row_pairs.append(f"{col}: {value}")
                if not row_pairs:
                    continue

                row_text = f"sheet={sheet_name}; row={row_idx}; " + " | ".join(row_pairs)
                chunks.append(
                    ExcelVectorChunk(
                        chunk_id=uuid.uuid4().hex,
                        content=row_text,
                        metadata={
                            "source_file": source_file,
                            "sheet": sheet_name,
                            "chunk_type": "row",
                            "row_index": row_idx,
                            "columns": columns[:50],
                        },
                    )
                )

            # 窗口分块：提升跨行问题召回能力
            row_records = normalized.to_dict(orient="records")
            for start in range(0, len(row_records), self._chunk_window_size):
                part = row_records[start : start + self._chunk_window_size]
                if not part:
                    continue

                rendered_rows: List[str] = []
                for rel_idx, record in enumerate(part, start=1):
                    items = []
                    for col in columns:
                        value = str(record.get(col, "")).strip()
                        if value:
                            items.append(f"{col}: {value}")
                    if items:
                        rendered_rows.append(
                            f"row={start + rel_idx}; " + " | ".join(items)
                        )

                if not rendered_rows:
                    continue

                window_text = (
                    f"sheet={sheet_name}; rows={start + 1}-{start + len(part)}\n"
                    + "\n".join(rendered_rows)
                )
                chunks.append(
                    ExcelVectorChunk(
                        chunk_id=uuid.uuid4().hex,
                        content=window_text,
                        metadata={
                            "source_file": source_file,
                            "sheet": sheet_name,
                            "chunk_type": "window",
                            "row_start": start + 1,
                            "row_end": start + len(part),
                            "columns": columns[:50],
                        },
                    )
                )
        return chunks


class ExcelVectorSearchApplicationService:
    def __init__(
        self,
        vector_store: Optional[VectorStorePort] = None,
        embedder: Optional[EmbedderPort] = None,
    ) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._embedder = embedder or HashEmbedder()

    def query(self, index_id: str, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        if not index_id:
            return {"success": False, "message": "缺少 index_id"}
        if not query_text:
            return {"success": False, "message": "缺少 query"}

        query_vector = self._embedder.embed_query(query_text)
        hits = self._vector_store.query(index_id=index_id, query_vector=query_vector, top_k=top_k)
        return {
            "success": True,
            "index_id": index_id,
            "query": query_text,
            "top_k": top_k,
            "hits": hits,
        }

    def list_indexes(self) -> Dict[str, Any]:
        return {"success": True, "indexes": self._vector_store.list_indexes()}

    def delete_index(self, index_id: str) -> Dict[str, Any]:
        deleted = self._vector_store.delete_index(index_id)
        return {"success": deleted, "index_id": index_id}


def _default_vector_db_path() -> str:
    env_path = os.environ.get("EXCEL_VECTOR_DB_PATH", "").strip()
    if env_path:
        folder = os.path.dirname(env_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        return env_path
    folder = os.path.join(get_app_data_dir(), "vectors")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "excel_vectors.db")


_sqlite_vector_store_instance: Optional[SQLiteVectorStore] = None
_pg_vector_store_instance: Optional[PgVectorStore] = None
_vector_store_instance: Optional[VectorStorePort] = None
_excel_vector_ingest_service_instance: Optional[ExcelVectorIngestApplicationService] = None
_excel_vector_search_service_instance: Optional[ExcelVectorSearchApplicationService] = None


def get_sqlite_vector_store() -> SQLiteVectorStore:
    global _sqlite_vector_store_instance
    if _sqlite_vector_store_instance is None:
        _sqlite_vector_store_instance = SQLiteVectorStore(db_path=_default_vector_db_path())
    return _sqlite_vector_store_instance


def get_pg_vector_store() -> PgVectorStore:
    global _pg_vector_store_instance
    if _pg_vector_store_instance is None:
        db_url = os.environ.get("VECTOR_DB_URL") or os.environ.get("DATABASE_URL")
        if not db_url:
            raise ValueError("缺少 VECTOR_DB_URL / DATABASE_URL 配置")
        _pg_vector_store_instance = PgVectorStore(database_url=db_url)
    return _pg_vector_store_instance


def get_vector_store() -> VectorStorePort:
    global _vector_store_instance
    if _vector_store_instance is not None:
        return _vector_store_instance
    use_sqlite_fallback = (os.environ.get("ENABLE_SQLITE_VECTOR_FALLBACK", "0") or "0").strip() == "1"
    if use_sqlite_fallback:
        _vector_store_instance = get_sqlite_vector_store()
    else:
        _vector_store_instance = get_pg_vector_store()
    return _vector_store_instance


def get_excel_vector_ingest_app_service() -> ExcelVectorIngestApplicationService:
    global _excel_vector_ingest_service_instance
    if _excel_vector_ingest_service_instance is None:
        _excel_vector_ingest_service_instance = ExcelVectorIngestApplicationService()
    return _excel_vector_ingest_service_instance


def get_excel_vector_search_app_service() -> ExcelVectorSearchApplicationService:
    global _excel_vector_search_service_instance
    if _excel_vector_search_service_instance is None:
        _excel_vector_search_service_instance = ExcelVectorSearchApplicationService()
    return _excel_vector_search_service_instance
