"""
无 PostgreSQL 依赖的统一 AI 槽位提取回归测试（不放在 backend/tests/ 下，避免 tests/conftest 的库级 Skip）。
运行：pytest backend/test_slot_filler_hyphen_model.py -q
"""

from __future__ import annotations

from backend.unified_ai.core.slot_filler import SlotFiller


def test_slot_filler_extracts_hyphen_model(monkeypatch):
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
            {"model_number": "777", "name": "A", "specification": "15KG/桶", "price": "12.8", "unit": "桶"},
            {"model_number": "303", "name": "B", "specification": "15KG/桶", "price": "11.0", "unit": "桶"},
            {"model_number": "3704", "name": "C", "specification": "18KG/桶", "price": "19.0", "unit": "桶"},
            {"model_number": "3708", "name": "D", "specification": "18KG/桶", "price": "20.0", "unit": "桶"},
            {"model_number": "7726-50f", "name": "E", "specification": "20KG/桶", "price": "22.0", "unit": "桶"},
        ],
    )

    filler = SlotFiller()
    text = "帮我打印一下深圳市柏木鼎家居有限公司的销售合同要三桶777和两桶，303和一桶3704和一桶3708和一桶7726-50f"

    import asyncio
    result = asyncio.run(filler.fill("sales_contract", {}, text, {}))

    assert result.success
    models = [p["model_number"] for p in result.slots["products"]]
    assert "7726-50f" in models
    assert "7726" not in models

    qty_map = {p["model_number"]: p["quantity"] for p in result.slots["products"]}
    assert qty_map["777"] == 3
    assert qty_map["303"] == 2
    assert qty_map["3704"] == 1
    assert qty_map["3708"] == 1
    assert qty_map["7726-50f"] == 1


def test_slot_filler_supports_compound_chinese_quantities(monkeypatch):
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
            {"model_number": "777", "name": "A", "specification": "15KG/桶", "price": "12.8", "unit": "桶"},
            {"model_number": "303", "name": "B", "specification": "15KG/桶", "price": "11.0", "unit": "桶"},
            {"model_number": "3704", "name": "C", "specification": "18KG/桶", "price": "19.0", "unit": "桶"},
            {"model_number": "3708", "name": "D", "specification": "18KG/桶", "price": "20.0", "unit": "桶"},
            {"model_number": "7726-50f", "name": "E", "specification": "20KG/桶", "price": "22.0", "unit": "桶"},
        ],
    )

    filler = SlotFiller()
    text = "帮我打印一下深圳市柏木鼎家居有限公司的销售合同要三十桶777和十二桶303和一桶3704和一统3708和一桶7726-50f"

    import asyncio
    result = asyncio.run(filler.fill("sales_contract", {}, text, {}))

    assert result.success
    qty_map = {p["model_number"]: p["quantity"] for p in result.slots["products"]}
    assert qty_map["777"] == 30
    assert qty_map["303"] == 12
    assert qty_map["3704"] == 1
    # 「一统」会规范为「一桶」后再解析，数量仍为 1
    assert qty_map["3708"] == 1
    assert qty_map["7726-50f"] == 1


def test_slot_filler_spoken_customer_and_fifty_buckets(monkeypatch):
    import asyncio

    import backend.routers.xcagi_compat as compat_mod

    monkeypatch.setattr(
        compat_mod,
        "_load_customers_rows",
        lambda: [{"customer_name": "惠州市丰驰家具有限公司"}],
    )
    monkeypatch.setattr(
        compat_mod,
        "_load_products_all_for_export",
        lambda keyword=None, unit=None: [
            {"model_number": "3100H", "name": "H产品", "specification": "20KG/桶", "price": "1", "unit": "桶"},
            {"model_number": "3706-50F", "name": "F产品", "specification": "18KG/桶", "price": "2", "unit": "桶"},
        ],
    )

    filler = SlotFiller()
    text = (
        "呃，帮我打印一下那个惠州市丰驰家居的那个销售合同"
        "我要三瓶慢干水。还有两桶的pu稀释剂和一统308和一桶的3706-50F，再来五十桶3100H。"
    )

    result = asyncio.run(filler.fill("sales_contract", {}, text, {}))
    assert result.success
    assert result.slots.get("customer_name") == "惠州市丰驰家居"

    qty_map = {p["model_number"]: int(p["quantity"]) for p in result.slots["products"]}
    assert qty_map["3100H"] == 50
    assert qty_map["3706-50F"] == 1
