"""
销售合同型号纠正回归测试（不放在 backend/tests/ 下，避免 tests/conftest 的库级 Skip）。
运行：pytest backend/test_sales_contract_model_resolution.py -q
"""

from __future__ import annotations

from backend.sales_contract_generate_core import _resolve_model_number


def test_resolve_model_number_keeps_exact_match():
    idx = {
        "7726-50f": {"model_number": "7726-50f"},
        "777": {"model_number": "777"},
    }
    assert _resolve_model_number("7726-50f", idx) == "7726-50f"


def test_resolve_model_number_maps_unique_hyphen_suffix():
    idx = {
        "7726-50f": {"model_number": "7726-50f"},
        "777": {"model_number": "777"},
    }
    assert _resolve_model_number("7726", idx) == "7726-50f"


def test_resolve_model_number_does_not_guess_when_ambiguous():
    idx = {
        "7726-50f": {"model_number": "7726-50f"},
        "7726-a1": {"model_number": "7726-a1"},
    }
    assert _resolve_model_number("7726", idx) == "7726"
