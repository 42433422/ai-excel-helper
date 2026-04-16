"""
合同校验型号容错回归测试（不放在 backend/tests/ 下，避免 tests/conftest 的库级 Skip）。
运行：pytest backend/test_contract_validator_model_resolution.py -q
"""

from __future__ import annotations

from backend.contract_validator import ContractValidator, _normalize_for_comparison
from backend.shared_utils import extract_customer_name


def _validator_with_products(products_index: dict[str, dict]):
    v = ContractValidator()
    v._products_index = products_index
    v._customers_index = {}
    return v


def test_validate_product_exact_model_ok():
    v = _validator_with_products(
        {
            "7726-50f": {"model_number": "7726-50f", "name": "测试品A"},
        }
    )
    out = v.validate_product("7726-50f")
    assert out["valid"] is True
    assert out["matched_product"]["model_number"] == "7726-50f"


def test_validate_product_auto_match_hyphen_suffix_when_unique():
    v = _validator_with_products(
        {
            "7726-50f": {"model_number": "7726-50f", "name": "测试品A"},
            "777": {"model_number": "777", "name": "测试品B"},
        }
    )
    out = v.validate_product("7726")
    assert out["valid"] is True
    assert out["matched_product"]["model_number"] == "7726-50f"


def test_validate_product_returns_suggestions_when_ambiguous():
    v = _validator_with_products(
        {
            "7726-50f": {"model_number": "7726-50f", "name": "测试品A"},
            "7726-a1": {"model_number": "7726-a1", "name": "测试品B"},
        }
    )
    out = v.validate_product("7726")
    assert out["valid"] is False
    assert "7726-50f" in out["suggestions"]
    assert "7726-a1" in out["suggestions"]


def test_extract_customer_name_compact_limited_company_in_long_utterance():
    s = "帮我打一下百木鼎家具有限公司的一个销售合同一个8828和一个303"
    assert extract_customer_name(s) == "百木鼎家具有限公司"


def test_validate_customer_aligns_long_utterance_via_find_matching(monkeypatch):
    """整句 customer_name：索引键与 _normalize_for_comparison 一致时须能通过 find_matching 回退。"""
    monkeypatch.setattr(
        "backend.shared_utils.find_matching_customer",
        lambda _s: "深圳市百木鼎家具有限公司",
    )
    v = ContractValidator()
    v._products_index = {}
    full = "深圳市百木鼎家具有限公司"
    key = _normalize_for_comparison(full)
    v._customers_index = {
        key: {
            "customer_name": full,
            "name": full,
            "unit_name": full,
        }
    }
    utterance = "帮我打一下百木鼎家具有限公司的一个销售合同一个8828"
    out = v.validate_customer(utterance)
    assert out["valid"] is True
    assert out["matched_customer"]["customer_name"] == full


def test_augment_validate_contract_client_fields():
    from backend.contract_validator import augment_validate_contract_client_fields

    r = {
        "valid": True,
        "customer_result": {
            "valid": True,
            "matched_customer": {"customer_name": "对齐客户有限公司", "name": "对齐客户有限公司"},
        },
        "valid_products": [{"model_number": "3100H", "quantity": 2, "name": "H"}],
    }
    out = augment_validate_contract_client_fields(r)
    assert out["customer_name"] == "对齐客户有限公司"
    assert out["products"][0]["model_number"] == "3100H"


def test_flatten_tool_result_dict_for_client_includes_nested_lists():
    from backend.tools import flatten_tool_result_dict_for_client

    raw = {
        "tool_key": "validate_contract",
        "valid": True,
        "customer_name": "某客户",
        "products": [{"model_number": "1", "quantity": 1}],
    }
    flat = flatten_tool_result_dict_for_client(raw)
    assert flat["customer_name"] == "某客户"
    assert flat["products"][0]["model_number"] == "1"
