"""
购买单位（客户）语义向量匹配：与 ``ProductSemanticMatcher`` 同源 BGE 嵌入，
用于整句/口语话术中识别 ``purchase_units.unit_name``。
"""

from __future__ import annotations

import logging
import os
import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"


class CustomerSemanticMatcher:
    """按 purchase_units 名称列表构建内存向量，查询为余弦相似度（L2 归一化后点积）。"""

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.environ.get("EMBEDDING_MODEL_ID", _DEFAULT_MODEL)
        self._model = None
        self._names: tuple[str, ...] = ()
        self._vectors: np.ndarray | None = None

    def _get_model(self):
        if self._model is None:
            from backend.torch_runtime_env import apply_sentence_transformers_compat_env

            apply_sentence_transformers_compat_env()
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_id)
        return self._model

    def set_unit_names(self, names: list[str]) -> None:
        """与当前 SQL 结果同步；名称集变化时重建向量。"""
        clean = [str(n).strip() for n in names if str(n).strip()]
        key = tuple(clean)
        if key == self._names and self._vectors is not None:
            return
        self._names = key
        self._vectors = None
        if not self._names:
            return
        model = self._get_model()
        # 轻量域前缀，便于与用户「客户/单位」表述对齐
        texts = [f"购买单位 {n}" for n in self._names]
        try:
            vecs = model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            self._vectors = np.asarray(vecs, dtype=np.float32)
            logger.info("customer semantic vectors built: n=%d", len(self._names))
        except Exception as e:
            logger.warning("customer semantic encode failed: %s", e)
            self._vectors = None

    def pick_best(
        self,
        queries: list[str],
        *,
        allowed: frozenset[str],
        min_score: float,
    ) -> tuple[str, float] | None:
        if self._vectors is None or not self._names:
            return None
        model = self._get_model()
        best_name: str | None = None
        best_score = -1.0
        for raw in queries:
            q = (raw or "").strip()
            if len(q) < 2:
                continue
            try:
                qv = model.encode(
                    [q],
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )[0].astype(np.float32)
                scores = self._vectors @ qv
                i = int(np.argmax(scores))
                s = float(scores[i])
                name = self._names[i]
                if name not in allowed:
                    continue
                if s > best_score:
                    best_score = s
                    best_name = name
            except Exception as e:
                logger.warning("customer semantic query encode failed: %s", e)
                continue
        if best_name is None or best_score < min_score:
            return None
        return (best_name, best_score)


_matcher: CustomerSemanticMatcher | None = None


def _get_singleton() -> CustomerSemanticMatcher | None:
    global _matcher
    if _matcher is None:
        try:
            _matcher = CustomerSemanticMatcher()
        except Exception as e:
            logger.warning("CustomerSemanticMatcher singleton failed: %s", e)
            return None
    return _matcher


def try_semantic_customer_pick(
    queries: list[str],
    *,
    unit_names: list[str],
    allowed: frozenset[str],
    min_score: float | None = None,
) -> str | None:
    """
    在给定的 ``purchase_units`` 名称集合上做语义检索，仅返回 ``allowed`` 内的命中。

    ``queries`` 按顺序尝试（如抽取片段、整句），先达到阈值的优先。
    """
    if os.environ.get("FHD_CUSTOMER_SEMANTIC", "1").strip().lower() in ("0", "false", "no", "off"):
        return None
    if not unit_names or not queries:
        return None
    thr = min_score if min_score is not None else float(os.environ.get("FHD_CUSTOMER_SEMANTIC_MIN_SCORE", "0.38"))
    m = _get_singleton()
    if m is None:
        return None
    try:
        m.set_unit_names(unit_names)
    except Exception as e:
        logger.debug("customer semantic set_unit_names: %s", e)
        return None
    if m._vectors is None:
        return None
    try:
        hit = m.pick_best(queries, allowed=allowed, min_score=thr)
        if hit:
            name, score = hit
            logger.info("customer semantic pick: score=%.3f name=%s", score, name)
            return name
    except Exception as e:
        logger.debug("try_semantic_customer_pick: %s", e)
    return None
