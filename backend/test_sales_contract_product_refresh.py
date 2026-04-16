"""
销售合同改编号刷新产品信息回归测试（纯函数级）。
运行：pytest backend/test_sales_contract_product_refresh.py -q
"""

from __future__ import annotations

from backend.sales_contract_generate_core import _pick_product_display_fields


def test_pick_product_display_fields_prefers_db_when_model_resolved():
    name, spec, price = _pick_product_display_fields(
        input_name="旧产品名",
        input_spec="旧规格",
        input_unit_price="99.9",
        db_product={
            "name": "新产品名",
            "specification": "15KG/桶",
            "price": "12.8",
        },
    )

    assert name == "新产品名"
    assert spec == "15KG/桶"
    assert price == 12.8


def test_pick_product_display_fields_falls_back_to_input_when_db_missing():
    name, spec, price = _pick_product_display_fields(
        input_name="手填产品",
        input_spec="20KG/桶",
        input_unit_price="18.5",
        db_product={},
    )

    assert name == "手填产品"
    assert spec == "20KG/桶"
    assert price == 18.5
