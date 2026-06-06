"""统一向量数据库引擎：所有 KB / 商品推荐 / 员工长期记忆共用一个 Chroma `PersistentClient`。

约定：
- 嵌入向量始终由调用方通过外部 embedding 服务（``embedding_service.embed_texts``）生成，
  这里 Chroma 的 ``embedding_function`` 强制为 ``None``，避免引入下载 ONNX 默认模型的副作用。
- 物理集合命名约定：
    - ``kb_<collection_id>``      用户/员工/工作流/组织 知识库（一个 SQL Collection 对应一个 Chroma 集合）
    - ``catalog_embeddings``       商品/MOD 推荐（保留旧名以兼容 ``vector_store.py``）
    - ``emp_<sanitized_pack_id>``  AI 员工长期记忆（per-employee_pack_id）
- 维度由调用方持久化在 SQL ``KnowledgeCollection.embedding_dim``，引擎不强制 1536。
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


logger = logging.getLogger(__name__)


class VectorEngineError(RuntimeError):
    """统一向量引擎抛出的错误（缺依赖、目录不可写、查询失败等）。"""


_lock = threading.Lock()
_client = None  # type: ignore[assignment]


def vector_db_dir() -> Path:
    """统一持久化目录：优先 ``MODSTORE_VECTOR_DB_DIR``；否则回落到 ``modstore_server/data/chroma``。"""
    raw = (os.environ.get("MODSTORE_VECTOR_DB_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "data" / "chroma"


def _legacy_vector_data_dir() -> Path:
    """旧 ``vector_store.py`` 的目录（``modstore_server/vector_data``），用于兼容存量数据。"""
    raw = (os.environ.get("MODSTORE_VECTOR_DB_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "vector_data"


def get_client():
    """懒加载、进程级单例 Chroma ``PersistentClient``。

    Raises:
        VectorEngineError: 未安装 ``chromadb``，或目录不可写。
    """
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is not None:
            return _client
        try:
            import chromadb
        except ImportError as e:  # noqa: BLE001
            raise VectorEngineError(
                "未安装 chromadb；请安装 'pip install chromadb' 或 'pip install \".[knowledge]\"'"
            ) from e

        path = vector_db_dir()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise VectorEngineError(f"无法创建向量库目录 {path}: {e}") from e

        try:
            client = chromadb.PersistentClient(path=str(path))
        except Exception as e:  # noqa: BLE001 — chromadb 自身异常类型多变
            raise VectorEngineError(f"初始化 Chroma PersistentClient 失败: {e}") from e

        _client = client
        logger.info("vector_engine: PersistentClient ready at %s", path)
        return _client


def reset_client_for_tests() -> None:
    """仅用于单测：丢弃当前单例，使下次 ``get_client`` 用新目录。"""
    global _client
    with _lock:
        _client = None


def _sanitize_collection_name(name: str) -> str:
    r"""Chroma 集合名约束：3-512 字节、ASCII、首尾字母数字、中间允许 ``. - _``。"""
    raw = (name or "").strip()
    safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in raw)
    safe = safe.strip("._-")
    if len(safe) < 3:
        safe = (safe + "_xx")[:3]
    return safe[:120]


def kb_collection_name(collection_id: int) -> str:
    """SQL ``KnowledgeCollection.id`` → Chroma 物理集合名。"""
    cid = int(collection_id)
    if cid <= 0:
        raise VectorEngineError("collection_id 必须为正整数")
    return f"kb_{cid}"


def employee_memory_collection_name(employee_pack_id: str) -> str:
    safe = _sanitize_collection_name(str(employee_pack_id or "default"))
    return f"emp_{safe}"


def get_or_create_collection(name: str, *, metadata: Optional[Dict[str, Any]] = None):
    """获取或新建 Chroma 集合。``embedding_function`` 强制 None：始终外部传入 embeddings。"""
    client = get_client()
    try:
        from chromadb.utils import embedding_functions  # noqa: F401  ensure module available
    except Exception:  # noqa: BLE001
        pass
    safe_name = _sanitize_collection_name(name)
    meta = {"hnsw:space": "cosine"}
    if metadata:
        for k, v in metadata.items():
            if v is None:
                continue
            meta[str(k)] = v
    try:
        return client.get_or_create_collection(
            name=safe_name,
            metadata=meta,
            embedding_function=None,
        )
    except TypeError:
        # 老版本 chromadb 不接受 embedding_function 关键字（>=0.5 才支持）；回退。
        return client.get_or_create_collection(name=safe_name, metadata=meta)


def get_collection(name: str):
    """读已存在集合。不存在抛 ``VectorEngineError``。"""
    client = get_client()
    safe_name = _sanitize_collection_name(name)
    try:
        return client.get_collection(name=safe_name)
    except Exception as e:  # noqa: BLE001
        raise VectorEngineError(f"集合不存在: {safe_name}") from e


def drop_collection(name: str, *, missing_ok: bool = True) -> bool:
    """删除整个 Chroma 集合（``KB`` 删除 / 重建用）。"""
    client = get_client()
    safe_name = _sanitize_collection_name(name)
    try:
        client.delete_collection(safe_name)
        return True
    except Exception as e:  # noqa: BLE001
        if missing_ok:
            return False
        raise VectorEngineError(f"删除集合失败: {safe_name}: {e}") from e


def upsert(
    collection_name: str,
    *,
    ids: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    documents: Sequence[str],
    metadatas: Optional[Sequence[Dict[str, Any]]] = None,
) -> int:
    """向集合 upsert 一批记录。返回写入条数。

    所有数组长度必须一致；空数组返回 0。
    """
    n = len(ids)
    if n == 0:
        return 0
    if len(embeddings) != n or len(documents) != n:
        raise VectorEngineError("ids/embeddings/documents 长度不一致")
    metas = list(metadatas) if metadatas else [{} for _ in range(n)]
    if len(metas) != n:
        raise VectorEngineError("metadatas 长度与 ids 不一致")

    cleaned_metas: List[Dict[str, Any]] = []
    for m in metas:
        cm: Dict[str, Any] = {}
        for k, v in (m or {}).items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                cm[str(k)] = v
            else:
                cm[str(k)] = str(v)
        cleaned_metas.append(cm or {"_": ""})  # Chroma 不接受空 metadata

    coll = get_or_create_collection(collection_name)
    try:
        coll.upsert(
            ids=[str(i) for i in ids],
            embeddings=[list(map(float, e)) for e in embeddings],
            documents=[str(d) for d in documents],
            metadatas=cleaned_metas,
        )
    except Exception as e:  # noqa: BLE001
        raise VectorEngineError(f"upsert 失败 collection={collection_name}: {e}") from e
    return n


def query(
    collection_name: str,
    *,
    query_embedding: Sequence[float],
    top_k: int = 6,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """KNN 查询。返回 ``[{id, document, metadata, distance}, ...]``，距离升序。"""
    n = max(1, min(int(top_k or 6), 100))
    try:
        coll = get_collection(collection_name)
    except VectorEngineError:
        return []
    where_clause: Optional[Dict[str, Any]] = None
    if where:
        clean = {k: v for k, v in where.items() if v is not None}
        if len(clean) == 1:
            (k, v) = next(iter(clean.items()))
            where_clause = {k: v}
        elif len(clean) > 1:
            where_clause = {"$and": [{k: {"$eq": v}} for k, v in clean.items()]}
    try:
        res = coll.query(
            query_embeddings=[list(map(float, query_embedding))],
            n_results=n,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:  # noqa: BLE001
        raise VectorEngineError(f"query 失败 collection={collection_name}: {e}") from e

    items: List[Dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0] or []
    docs = (res.get("documents") or [[]])[0] or []
    metas = (res.get("metadatas") or [[]])[0] or []
    dists = (res.get("distances") or [[]])[0] or []
    for i, _id in enumerate(ids):
        items.append(
            {
                "id": str(_id),
                "document": str(docs[i]) if i < len(docs) else "",
                "metadata": dict(metas[i]) if i < len(metas) and isinstance(metas[i], dict) else {},
                "distance": float(dists[i]) if i < len(dists) else 1.0,
            }
        )
    return items


def delete(
    collection_name: str,
    *,
    ids: Optional[Sequence[str]] = None,
    where: Optional[Dict[str, Any]] = None,
) -> int:
    """删除指定 ids 或按 metadata where 过滤删除；返回删除数量（best-effort）。"""
    try:
        coll = get_collection(collection_name)
    except VectorEngineError:
        return 0
    before = 0
    try:
        before = int(coll.count())
    except Exception:  # noqa: BLE001
        pass
    where_clause: Optional[Dict[str, Any]] = None
    if where:
        clean = {k: v for k, v in where.items() if v is not None}
        if len(clean) == 1:
            (k, v) = next(iter(clean.items()))
            where_clause = {k: v}
        elif len(clean) > 1:
            where_clause = {"$and": [{k: {"$eq": v}} for k, v in clean.items()]}
    try:
        coll.delete(
            ids=[str(i) for i in ids] if ids else None,
            where=where_clause,
        )
    except Exception as e:  # noqa: BLE001
        raise VectorEngineError(f"delete 失败 collection={collection_name}: {e}") from e
    after = 0
    try:
        after = int(coll.count())
    except Exception:  # noqa: BLE001
        pass
    return max(0, before - after)


def count(collection_name: str) -> int:
    """集合文档总数；集合不存在返回 0。"""
    try:
        coll = get_collection(collection_name)
    except VectorEngineError:
        return 0
    try:
        return int(coll.count())
    except Exception:  # noqa: BLE001
        return 0


def status() -> Dict[str, Any]:
    """诊断信息（给 ``/api/knowledge/status`` 与 ``/v2/status`` 用）。"""
    out: Dict[str, Any] = {
        "backend": "chroma",
        "persist_dir": str(vector_db_dir()),
        "ready": False,
        "collections": 0,
        "error": "",
    }
    try:
        client = get_client()
        try:
            cols = client.list_collections()
            out["collections"] = len(list(cols))
        except Exception:  # noqa: BLE001
            out["collections"] = 0
        out["ready"] = True
    except VectorEngineError as e:
        out["error"] = str(e)
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def get_or_create_engine_collection_for_kb(collection_id: int):
    """便捷封装：根据 SQL collection_id 获取/建立物理集合。"""
    return get_or_create_collection(kb_collection_name(int(collection_id)))


__all__ = [
    "VectorEngineError",
    "vector_db_dir",
    "get_client",
    "reset_client_for_tests",
    "kb_collection_name",
    "employee_memory_collection_name",
    "get_or_create_collection",
    "get_collection",
    "drop_collection",
    "upsert",
    "query",
    "delete",
    "count",
    "status",
    "get_or_create_engine_collection_for_kb",
]
