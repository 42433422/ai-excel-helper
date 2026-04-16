"""
无 PostgreSQL 依赖的型号解析回归测试（不放在 backend/tests/ 下，避免 tests/conftest 的库级 Skip）。
运行：pytest backend/test_user_input_parser_hyphen_model.py -q
"""

from __future__ import annotations

import backend.sales_contract_intent_bridge as sc_bridge
from backend import user_input_parser as parser_mod


def test_extract_structured_info_keeps_hyphen_model(monkeypatch):
    monkeypatch.setattr(parser_mod, "_try_llm_extraction", lambda _: None)
    monkeypatch.setattr(sc_bridge, "sales_contract_utterance_requires_structured_llm", lambda _: False)
    monkeypatch.setattr(
        parser_mod,
        "_load_customers_set",
        lambda: {"深圳市柏木鼎家居有限公司"},
    )
    monkeypatch.setattr(
        parser_mod,
        "_load_products_set",
        lambda: {"777", "303", "3704", "3708", "7726-50f"},
    )

    message = "帮我打印一下深圳市柏木鼎家居有限公司的销售合同要三桶777和两桶，303和一桶3704和一桶3708和一桶7726-50f"
    result = parser_mod.extract_structured_info(message)

    assert result["customer_name"] == "深圳市柏木鼎家居有限公司"
    assert "7726-50f" in result["products"]
    assert result["quantities"]["7726-50f"] == 1
    assert result["quantities"]["777"] == 3
    assert result["quantities"]["303"] == 2
    assert result["quantities"]["3704"] == 1
    assert result["quantities"]["3708"] == 1


def test_extract_structured_info_hyphen_model_after_bianhao(monkeypatch):
    monkeypatch.setattr(parser_mod, "_try_llm_extraction", lambda _: None)
    monkeypatch.setattr(parser_mod, "_load_customers_set", lambda: set())
    monkeypatch.setattr(parser_mod, "_load_products_set", lambda: {"7726-50f"})

    result = parser_mod.extract_structured_info("编号 7726-50f 要一桶")

    assert result["products"] == ["7726-50f"]
    assert result["quantities"]["7726-50f"] == 1


def test_extract_structured_info_supports_compound_chinese_quantities(monkeypatch):
    monkeypatch.setattr(parser_mod, "_try_llm_extraction", lambda _: None)
    monkeypatch.setattr(sc_bridge, "sales_contract_utterance_requires_structured_llm", lambda _: False)
    monkeypatch.setattr(
        parser_mod,
        "_load_customers_set",
        lambda: {"深圳市柏木鼎家居有限公司"},
    )
    monkeypatch.setattr(
        parser_mod,
        "_load_products_set",
        lambda: {"777", "303", "3704", "3708", "7726-50f"},
    )

    message = "帮我打印一下深圳市柏木鼎家居有限公司的销售合同要三十桶777和十二桶303和一桶3704和一统3708和一桶7726-50f"
    result = parser_mod.extract_structured_info(message)

    assert result["customer_name"] == "深圳市柏木鼎家居有限公司"
    assert result["quantities"]["777"] == 30
    assert result["quantities"]["303"] == 12
    assert result["quantities"]["3704"] == 1
    # “一统3708”不是标准“桶”，会走兜底型号识别，数量默认 1
    assert result["quantities"]["3708"] == 1
    assert result["quantities"]["7726-50f"] == 1
