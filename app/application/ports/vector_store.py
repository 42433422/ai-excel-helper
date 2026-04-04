from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStorePort(ABC):
    """向量存储端口。"""

    @abstractmethod
    def upsert_chunks(
        self,
        index_id: str,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """写入分块向量数据并返回写入数量。"""
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        index_id: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """检索相似分块。"""
        raise NotImplementedError

    @abstractmethod
    def list_indexes(self) -> List[Dict[str, Any]]:
        """返回索引列表与状态。"""
        raise NotImplementedError

    @abstractmethod
    def delete_index(self, index_id: str) -> bool:
        """删除索引。"""
        raise NotImplementedError
