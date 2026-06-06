from __future__ import annotations

from abc import ABC, abstractmethod


class EmbedderPort(ABC):
    """文本嵌入模型端口。"""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量生成文本向量。"""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """生成查询向量。"""
        raise NotImplementedError
