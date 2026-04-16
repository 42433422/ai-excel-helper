"""
按产品名称提取并生成产品槽位回归测试（不放在 backend/tests/ 下，避免 tests/conftest 的库级 Skip）。
运行：pytest backend/test_slot_filler_product_name.py -q
"""

from __future__ import annotations

import asyncio

from backend.unified_ai.core.slot_filler import SlotFiller


def test_slot_filler_extracts_products_by_name(monkeypatch):
    import backend.routers.xcagi_compat as compat_mod

    monkeypatch.setattr(
        compat_mod,
        "_load_customers_rows",
        lambda: [{"customer_name": "深圳市柏木鼎家居有限公司"}],
    )
    monkeypatch.setattr(
        compat_mod,
        "_load_products_all_for_export",
        lambda keyword=None, unit=None: [
            {"model_number": "777", "name": "PU天那水(面水)", "specification": "15KG/桶", "price": "12.8", "unit": "桶"},
            {"model_number": "303", "name": "PU稀释剂303", "specification": "15KG/桶", "price": "11.0", "unit": "桶"},
        ],
    )

    filler = SlotFiller()
    text = "帮我生成发货单，深圳市柏木鼎家居有限公司要三桶PU天那水(面水)和两桶PU稀释剂303"
    result = asyncio.run(filler.fill("shipment_generate", {}, text, {}))

    assert result.success
    products = result.slots["products"]
    qty_map = {p["model_number"]: p["quantity"] for p in products}
    assert qty_map["777"] == 3
    assert qty_map["303"] == 2


def test_slot_filler_extract_model_number_by_name(monkeypatch):
    import backend.routers.xcagi_compat as compat_mod

    monkeypatch.setattr(
        compat_mod,
        "_load_products_all_for_export",
        lambda keyword=None, unit=None: [
            {"model_number": "777", "name": "PU天那水(面水)", "specification": "15KG/桶", "price": "12.8", "unit": "桶"},
        ],
    )

    filler = SlotFiller()
    model = filler._extract_model_number("打印标签 PU天那水(面水) 三张", {})
    assert model == "777"
