"""
产品语义匹配模块：使用向量嵌入实现产品名称/型号的语义相似度匹配。
解决用户输入"七彩乐园9803"时能匹配到数据库中的"七彩乐园 9803"类似产品。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_EMBEDDER: "ProductSemanticMatcher | None" = None


def _get_default_embedder() -> "ProductSemanticMatcher | None":
    global _EMBEDDER
    if _EMBEDDER is None:
        try:
            _EMBEDDER = ProductSemanticMatcher()
            _EMBEDDER.ensure_index_built()
        except Exception as e:
            logger.warning("failed to init ProductSemanticMatcher: %s", e)
            return None
    return _EMBEDDER


def _normalize_text_for_match(text: str) -> str:
    """文本标准化：去除空格、转小写、去除特殊字符"""
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace(" ", "").replace("　", "")
    return text


class ProductSemanticMatcher:
    """
    使用 BGE 语义嵌入对产品名称/型号进行向量匹配。
    支持模糊语义搜索，帮助找到与用户输入最相似的产品。
    """

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.environ.get("EMBEDDING_MODEL_ID", "BAAI/bge-small-zh-v1.5")
        self._embedder = None
        self._products: list[dict[str, Any]] = []
        self._name_vectors: np.ndarray | None = None
        self._model_vectors: np.ndarray | None = None
        self._index_built = False

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from backend.torch_runtime_env import apply_sentence_transformers_compat_env

                apply_sentence_transformers_compat_env()
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer(self.model_id)
            except ImportError:
                logger.warning("sentence_transformers not installed, semantic match unavailable")
                return None
            except Exception as e:
                logger.warning("failed to load embedding model: %s", e)
                return None
        return self._embedder

    def _load_products_from_db(self) -> list[dict[str, Any]]:
        """从数据库加载产品列表"""
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export
            return _load_products_all_for_export(keyword=None, unit=None)
        except Exception as e:
            logger.warning("failed to load products for semantic match: %s", e)
            return []

    def _build_text_representation(self, product: dict[str, Any]) -> str:
        """构建产品的文本表示，用于生成向量"""
        parts = []
        name = (product.get("name") or "").strip()
        model = (product.get("model_number") or "").strip()
        spec = (product.get("specification") or "").strip()
        if name:
            parts.append(name)
        if model:
            parts.append(f"型号{model}")
        if spec:
            parts.append(f"规格{spec}")
        return " ".join(parts)

    def ensure_index_built(self) -> bool:
        """确保向量索引已构建（惰性加载）"""
        if self._index_built:
            return True
        return self.build_index()

    def build_index(self) -> bool:
        """
        从数据库加载产品并构建向量索引。
        Returns:
            True if index built successfully, False otherwise
        """
        embedder = self._get_embedder()
        if embedder is None:
            logger.warning("embedder not available, cannot build index")
            return False

        products = self._load_products_from_db()
        if not products:
            logger.warning("no products loaded from database")
            return False

        self._products = products

        name_texts = [self._build_text_representation(p) for p in products]

        try:
            name_vectors = embedder.encode(
                name_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            self._name_vectors = name_vectors.astype(np.float32)
        except Exception as e:
            logger.error("failed to encode product vectors: %s", e)
            return False

        self._model_vectors = None
        self._index_built = True
        logger.info("product semantic index built: %d products", len(products))
        return True

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        语义搜索相似产品。

        Args:
            query: 用户输入的查询文本（如 "七彩乐园9803"）
            top_k: 返回最多 top_k 个结果
            min_score: 最低相似度阈值（0-1）

        Returns:
            匹配的产品列表，每个产品包含 score（相似度）和产品信息
        """
        if not self.ensure_index_built():
            return []

        if not query or not query.strip():
            return []

        embedder = self._get_embedder()
        if embedder is None or self._name_vectors is None:
            return []

        try:
            q_vec = embedder.encode(
                [query.strip()],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0].astype(np.float32)

            scores = self._name_vectors @ q_vec

            k = min(top_k * 2, len(scores))
            idx = np.argpartition(-scores, k - 1)[:k]
            idx = idx[np.argsort(-scores[idx])]

            results = []
            for i in idx:
                score = float(scores[i])
                if score < min_score:
                    continue
                product = dict(self._products[int(i)])
                product["_match_score"] = score
                product["_match_query"] = query
                results.append(product)
                if len(results) >= top_k:
                    break

            return results

        except Exception as e:
            logger.error("semantic search failed: %s", e)
            return []

    def find_by_model_number(self, model_number: str) -> list[dict[str, Any]]:
        """
        根据型号精确查找产品（支持模糊匹配）
        """
        if not model_number or not self._products:
            return []

        norm_input = _normalize_text_for_match(model_number)
        results = []

        for p in self._products:
            model = (p.get("model_number") or "").strip()
            if not model:
                continue

            norm_model = _normalize_text_for_match(model)

            if norm_input == norm_model or norm_input in norm_model or norm_model in norm_input:
                results.append(dict(p))

        return results

    def find_by_name(self, name: str) -> list[dict[str, Any]]:
        """
        根据产品名称查找（支持模糊匹配）
        """
        if not name or not self._products:
            return []

        norm_input = _normalize_text_for_match(name)
        results = []

        for p in self._products:
            p_name = (p.get("name") or "").strip()
            if not p_name:
                continue

            norm_p_name = _normalize_text_for_match(p_name)

            if norm_input in norm_p_name or norm_p_name in norm_input:
                results.append(dict(p))

        return results

    def match_product(self, user_input: str) -> dict[str, Any] | None:
        """
        综合匹配：先用语义搜索，再用模糊匹配作为备选。

        Args:
            user_input: 用户输入的产品描述

        Returns:
            最佳匹配产品或 None
        """
        if not user_input or not user_input.strip():
            return None

        user_input = user_input.strip()

        semantic_results = self.search(user_input, top_k=1, min_score=0.35)
        if semantic_results:
            return semantic_results[0]

        model_results = self.find_by_model_number(user_input)
        if model_results:
            return model_results[0]

        name_results = self.find_by_name(user_input)
        if name_results:
            return name_results[0]

        return None


def semantic_match_product(user_input: str) -> dict[str, Any] | None:
    """
    全局函数：使用语义匹配找到最佳产品。
    优先使用向量语义相似度，其次使用模糊字符串匹配。
    """
    matcher = _get_default_embedder()
    if matcher is None:
        logger.warning("ProductSemanticMatcher not available, falling back to simple match")
        return _simple_product_match(user_input)

    return matcher.match_product(user_input)


def _simple_product_match(user_input: str) -> dict[str, Any] | None:
    """
    简单的产品匹配（无向量能力时的备选方案）
    """
    try:
        from backend.routers.xcagi_compat import _load_products_all_for_export
        products = _load_products_all_for_export(keyword=None, unit=None)
    except Exception:
        return None

    if not products:
        return None

    norm_input = _normalize_text_for_match(user_input)
    if not norm_input:
        return None

    best_match = None
    best_score = 0

    for p in products:
        name = _normalize_text_for_match(p.get("name") or "")
        model = _normalize_text_for_match(p.get("model_number") or "")

        if not name and not model:
            continue

        if norm_input == name or norm_input == model:
            return p

        score = 0
        if name and norm_input in name:
            score = len(norm_input) / len(name)
        elif model and norm_input in model:
            score = len(norm_input) / len(model)

        if score > best_score:
            best_score = score
            best_match = p

    return best_match if best_score > 0.5 else None