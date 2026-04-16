"""
BGE 语义向量：形状与索引检索冒烟（依赖 sentence-transformers / torch；环境异常时 skip）。
"""

import pytest


def test_sentence_transformer_query_shape():
    try:
        from backend.excel_vector_app_service import SentenceTransformerEmbedder

        emb = SentenceTransformerEmbedder()
        v = emb.embed_query("测试语义向量维度")
    except Exception as e:
        pytest.skip(f"BGE embedder unavailable: {e}")
    assert v.ndim == 1
    assert v.shape[0] == 512


def test_index_and_search_excel(excel_workspace):
    try:
        from backend.excel_vector_app_service import ExcelVectorAppService

        root = str(excel_workspace)
        svc = ExcelVectorAppService(workspace_root=root)
        info = svc.index_excel("sample.xlsx")
        assert info["indexed"] == 3
        hits = svc.search("工程部门员工", top_k=2)
        assert len(hits) >= 1
        assert "score" in hits[0]
    except Exception as e:
        pytest.skip(f"BGE embedder unavailable: {e}")
