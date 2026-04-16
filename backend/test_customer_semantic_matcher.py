"""
客户语义匹配（可选 BGE）。不放入 backend/tests/，避免 conftest 的库级 Skip。
运行：pytest backend/test_customer_semantic_matcher.py -q
"""

from __future__ import annotations

import os


def test_semantic_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("FHD_CUSTOMER_SEMANTIC", "0")
    from backend.customer_semantic_matcher import try_semantic_customer_pick

    assert (
        try_semantic_customer_pick(
            ["帮我找某公司"],
            unit_names=["深圳市百木鼎家具有限公司"],
            allowed=frozenset({"深圳市百木鼎家具有限公司"}),
        )
        is None
    )


def test_semantic_pick_when_model_available():
    os.environ.pop("FHD_CUSTOMER_SEMANTIC", None)
    from backend.customer_semantic_matcher import try_semantic_customer_pick

    names = ["惠州市枫驰家具有限公司", "深圳市百木鼎家具有限公司"]
    allowed = frozenset(names)
    q = "帮我打一下百木鼎家具有限公司的销售合同"
    try:
        hit = try_semantic_customer_pick([q], unit_names=names, allowed=allowed, min_score=0.35)
    except Exception as e:
        import pytest

        pytest.skip(f"BGE / sentence-transformers 不可用: {e}")
    assert hit == "深圳市百木鼎家具有限公司"
