"""
Excel row indexing and semantic search using sentence-transformers (BGE).

Embeddings are L2-normalized so dot product equals cosine similarity.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.tools import resolve_safe_excel_path

# bge-small-zh-v1.5 produces 512-d vectors
_DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"


class SentenceTransformerEmbedder:
    """
    Lazy-loaded sentence-transformers embedder. Replaces a trivial hash embedder
    with dense semantic vectors. Query and passage prefixes follow BGE retrieval usage.
    """

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.environ.get("EMBEDDING_MODEL_ID", _DEFAULT_MODEL)
        self._model = None

    def _get_model(self):
        if self._model is None:
            from backend.torch_runtime_env import apply_sentence_transformers_compat_env

            apply_sentence_transformers_compat_env()
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_id)
        return self._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Encode passages for indexing. L2-normalized (cosine via dot product)."""
        if not texts:
            return np.zeros((0, 512), dtype=np.float32)
        model = self._get_model()
        prefix = os.environ.get("BGE_DOC_PREFIX", "")
        passages = [(prefix + t) if t else " " for t in texts]
        emb = model.encode(
            passages,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(emb, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """Single query vector (shape (512,))."""
        model = self._get_model()
        prefix = os.environ.get("BGE_QUERY_PREFIX", "")
        q = (prefix + text) if text.strip() else " "
        emb = model.encode(
            [q],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(emb, dtype=np.float32)[0]

    def embed_texts(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        """Batch API: if is_query, encode each string with the query side settings."""
        if not texts:
            return np.zeros((0, 512), dtype=np.float32)
        if is_query:
            return np.stack([self.embed_query(t) for t in texts], axis=0)
        return self.embed_documents(texts)


@dataclass
class _Chunk:
    text: str
    vector: np.ndarray
    meta: dict[str, Any]


@dataclass
class ExcelVectorAppService:
    """
    In-memory vector index over Excel rows. Each row becomes a text line from
    stringified column values for embedding.
    """

    workspace_root: str
    embedder: SentenceTransformerEmbedder | None = None
    _chunks: list[_Chunk] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.embedder is None:
            self.embedder = SentenceTransformerEmbedder()

    def clear(self) -> None:
        self._chunks.clear()

    def index_excel(
        self,
        file_path: str,
        *,
        sheet_name: str | int | None = None,
        columns: list[str] | None = None,
        header_row: int = 0,
        max_rows: int | None = None,
        extra_prefix: str = "",
    ) -> dict[str, Any]:
        path = resolve_safe_excel_path(self.workspace_root, file_path)
        if not path.is_file():
            raise FileNotFoundError(str(path))

        kwargs: dict[str, Any] = {"engine": "openpyxl", "header": header_row}
        kwargs["sheet_name"] = 0 if sheet_name is None else sheet_name
        df = pd.read_excel(path, **kwargs)
        if columns:
            df = df[[c for c in columns if c in df.columns]]
        if max_rows is not None:
            df = df.head(max_rows)

        texts: list[str] = []
        metas: list[dict[str, Any]] = []
        for idx, row in df.iterrows():
            parts = [f"{k}={v}" for k, v in row.items() if pd.notna(v)]
            line = extra_prefix + " | ".join(str(p) for p in parts)
            texts.append(line[:8000])
            metas.append({"file_path": file_path, "row_index": int(idx) if isinstance(idx, (int, np.integer)) else str(idx)})

        if not texts:
            return {"indexed": 0, "file_path": file_path}

        assert self.embedder is not None
        vecs = self.embedder.embed_documents(texts)
        for t, v, m in zip(texts, vecs, metas, strict=True):
            self._chunks.append(_Chunk(text=t, vector=v.astype(np.float32), meta=m))

        return {"indexed": len(texts), "file_path": file_path, "total_chunks": len(self._chunks)}

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self._chunks or not query.strip():
            return []
        assert self.embedder is not None
        q = self.embedder.embed_query(query)
        mat = np.stack([c.vector for c in self._chunks], axis=0)
        scores = mat @ q
        k = min(top_k, len(scores))
        idx = np.argpartition(-scores, k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]
        out: list[dict[str, Any]] = []
        for i in idx:
            c = self._chunks[int(i)]
            out.append(
                {
                    "score": float(scores[int(i)]),
                    "text": c.text,
                    "meta": c.meta,
                }
            )
        return out

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


# Backwards-compatible alias if older code imported HashEmbedder
HashEmbedder = SentenceTransformerEmbedder
