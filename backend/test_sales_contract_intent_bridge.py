"""
销售合同 intent bridge 单测（不依赖真实 LLM；monkeypatch extract）。
运行：pytest backend/test_sales_contract_intent_bridge.py -q
"""

from __future__ import annotations

import backend.sales_contract_intent_bridge as bridge
from backend.sales_contract_intent_bridge import (
    DraftLine,
    SalesContractDraft,
    merge_planner_sales_contract_args,
    message_suggests_sales_contract,
    resolve_draft_to_tool_slots,
    sales_contract_tool_args_need_bridge,
    sales_contract_utterance_requires_structured_llm,
)

# 前端冒烟常用长句（与 #messageInput 手工输入一致）
_FENGCHI_SMOKE_UTTERANCE = (
    "呃，帮我打印一下那个惠州市丰驰家居的那个销售合同我要三瓶慢干水。"
    "还有两桶的pu稀释剂和一统308和一桶的3706-50F，再来五十桶3100H。"
)


def test_resolve_draft_skips_bulk_customer_hint_uses_raw_extract(monkeypatch):
    utter = "呃，帮我打印一下那个惠州市丰驰家居的那个销售合同我要三瓶慢干水。"
    monkeypatch.setattr(
        "backend.routers.xcagi_compat._load_products_all_for_export",
        lambda keyword=None, unit=None: [
            {"model_number": "3100H", "name": "H", "specification": "20KG/桶", "price": "1", "unit": "桶"},
        ],
    )
    monkeypatch.setattr(
        "backend.product_db_read.find_matching_customer_unified",
        lambda hint: "惠州市丰驰家具有限公司" if "丰驰" in hint else None,
    )
    draft = SalesContractDraft(
        customer_hint=utter,
        lines=[DraftLine(model_hint="3100H", quantity=2)],
    )
    slots = resolve_draft_to_tool_slots(draft, raw_user_message=utter)
    assert slots is not None
    assert slots["customer_name"] == "惠州市丰驰家具有限公司"


def test_resolve_repairs_pu_model_to_diluent_name(monkeypatch):
    raw = "两桶pu稀释剂再来五十桶3100H"
    monkeypatch.setattr(
        "backend.routers.xcagi_compat._load_products_all_for_export",
        lambda keyword=None, unit=None: [
            {"model_number": "PU", "name": "", "specification": "", "price": "0", "unit": "桶"},
            {"model_number": "3100H", "name": "H", "specification": "20KG/桶", "price": "2", "unit": "桶"},
            {"model_number": "DIL1", "name": "PU稀释剂", "specification": "15KG/桶", "price": "4", "unit": "桶"},
        ],
    )
    monkeypatch.setattr("backend.product_db_read.find_matching_customer_unified", lambda h: None)
    draft = SalesContractDraft(
        customer_hint=None,
        lines=[
            DraftLine(model_hint="PU", quantity=2),
            DraftLine(model_hint="3100H", quantity=50),
        ],
    )
    slots = resolve_draft_to_tool_slots(draft, raw_user_message=raw)
    assert slots is not None
    by_m = {p["model_number"]: int(p["quantity"]) for p in slots["products"]}
    assert by_m == {"DIL1": 2, "3100H": 50}


def test_resolve_disambiguates_duplicate_model_by_name_hint(monkeypatch):
    """同规范化型号多行时，用语义品名消歧（对齐发货单 match_product 思路）。"""
    rows = [
        {"model_number": "308X", "name": "慢干水专用", "specification": "10KG/桶", "price": "1", "unit": "桶"},
        {"model_number": "308X", "name": "高光面漆", "specification": "18KG/桶", "price": "2", "unit": "桶"},
    ]
    monkeypatch.setattr(
        "backend.routers.xcagi_compat._load_products_all_for_export",
        lambda keyword=None, unit=None: rows,
    )
    monkeypatch.setattr("backend.product_db_read.find_matching_customer_unified", lambda h: None)
    draft = SalesContractDraft(
        customer_hint=None,
        lines=[DraftLine(model_hint="308X", name_hint="慢干水", quantity=2)],
    )
    slots = resolve_draft_to_tool_slots(draft, raw_user_message="要两桶308X慢干水")
    assert slots is not None
    assert len(slots["products"]) == 1
    assert slots["products"][0]["model_number"] == "308X"
    assert "慢干" in slots["products"][0]["name"]


def test_resolve_draft_to_tool_slots(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.xcagi_compat._load_products_all_for_export",
        lambda keyword=None, unit=None: [
            {"model_number": "3100H", "name": "H", "specification": "20KG/桶", "price": "1", "unit": "桶"},
            {"model_number": "3706-50F", "name": "F", "specification": "18KG/桶", "price": "2", "unit": "桶"},
        ],
    )
    monkeypatch.setattr(
        "backend.product_db_read.find_matching_customer_unified",
        lambda hint: "惠州市丰驰家具有限公司" if "丰驰" in hint else None,
    )

    draft = SalesContractDraft(
        customer_hint="惠州市丰驰家居",
        lines=[
            DraftLine(model_hint="3706-50F", quantity=1),
            DraftLine(model_hint="3100H", quantity=50),
        ],
    )
    slots = resolve_draft_to_tool_slots(draft)
    assert slots is not None
    assert slots["customer_name"] == "惠州市丰驰家具有限公司"
    q = {p["model_number"]: int(p["quantity"]) for p in slots["products"]}
    assert q["3706-50F"] == 1
    assert q["3100H"] == 50


def test_merge_planner_sales_contract_args(monkeypatch):
    monkeypatch.setattr(
        bridge,
        "extract_sales_contract_draft",
        lambda _: SalesContractDraft(
            customer_hint="惠州市丰驰家居",
            lines=[DraftLine(model_hint="3100H", quantity=2)],
        ),
    )
    monkeypatch.setattr(
        bridge,
        "resolve_draft_to_tool_slots",
        lambda *_a, **_k: {
            "customer_name": "惠州市丰驰家具有限公司",
            "products": [{"model_number": "3100H", "quantity": "2"}],
        },
    )

    args = {
        "customer_name": "呃，帮我打印一下那个惠州市丰驰家居的那个销售合同我要三瓶慢干水",
        "products": [{"model_number": "", "quantity": "1"}],
    }
    out = merge_planner_sales_contract_args(args, "原始用户话")
    assert out["customer_name"] == "惠州市丰驰家具有限公司"
    assert out["products"][0]["model_number"] == "3100H"


def test_merge_planner_sales_contract_args_coerces_customer_as_utterance(monkeypatch):
    """并行线程无 user_message 时，用整句 ``customer_name`` 触发 bridge。"""
    monkeypatch.setattr(
        bridge,
        "extract_sales_contract_draft",
        lambda _: SalesContractDraft(
            customer_hint="惠州市丰驰家居",
            lines=[DraftLine(model_hint="3100H", quantity=2)],
        ),
    )
    monkeypatch.setattr(
        bridge,
        "resolve_draft_to_tool_slots",
        lambda *_a, **_k: {
            "customer_name": "惠州市丰驰家具有限公司",
            "products": [{"model_number": "3100H", "quantity": "2"}],
        },
    )
    long_cn = "呃，帮我打印一下那个惠州市丰驰家居的那个销售合同我要三瓶慢干水"
    args = {
        "customer_name": long_cn,
        "products": [{"model_number": "", "quantity": "1"}],
    }
    out = merge_planner_sales_contract_args(args, None)
    assert out["customer_name"] == "惠州市丰驰家具有限公司"
    assert out["products"][0]["model_number"] == "3100H"


def test_sales_contract_tool_args_need_bridge():
    long_cn = "呃，帮我打印一下那个惠州市丰驰家居的那个销售合同我要三瓶"
    assert sales_contract_tool_args_need_bridge({"customer_name": long_cn, "products": [{"model_number": "1"}]}, "x")
    assert not sales_contract_tool_args_need_bridge({"customer_name": "某公司", "products": [{"model_number": "308"}]}, None)


def test_message_suggests_sales_contract_fengchi_smoke():
    assert message_suggests_sales_contract(_FENGCHI_SMOKE_UTTERANCE)


def test_sales_contract_utterance_requires_structured_llm_fengchi():
    assert sales_contract_utterance_requires_structured_llm(_FENGCHI_SMOKE_UTTERANCE)


def test_sales_contract_utterance_requires_structured_llm_short_rule_friendly():
    s = "销售合同8828三桶"
    assert message_suggests_sales_contract(s)
    assert not sales_contract_utterance_requires_structured_llm(s)


def test_merge_planner_prefers_llm_on_oral_long_utterance_even_if_args_look_ok(monkeypatch):
    """口语长单：即使模型参数未触发 need_bridge，仍应以原话走 LLM 合并。"""
    monkeypatch.setattr(
        bridge,
        "extract_sales_contract_draft",
        lambda _: SalesContractDraft(
            customer_hint="惠州市丰驰家居",
            lines=[DraftLine(model_hint="3100H", quantity=50)],
        ),
    )
    monkeypatch.setattr(
        bridge,
        "resolve_draft_to_tool_slots",
        lambda *_a, **_k: {
            "customer_name": "惠州市丰驰家具有限公司",
            "products": [{"model_number": "3100H", "quantity": "50"}],
        },
    )
    utter = _FENGCHI_SMOKE_UTTERANCE
    args = {"customer_name": "惠州市丰驰家居", "products": [{"model_number": "3100H", "quantity": "50"}]}
    out = merge_planner_sales_contract_args(dict(args), utter)
    assert out["customer_name"] == "惠州市丰驰家具有限公司"


def test_merge_planner_fengchi_full_user_smoke(monkeypatch):
    """Planner 传入完整用户原话时，bridge 应对坏参数做合并（抽取结果此处用 mock）。"""
    captured: list[str] = []

    def _capture_extract(text: str) -> SalesContractDraft:
        captured.append(text)
        return SalesContractDraft(
            customer_hint="惠州市丰驰家居",
            lines=[
                DraftLine(name_hint="慢干水", quantity=3),
                DraftLine(name_hint="PU稀释剂", quantity=2),
                DraftLine(model_hint="308", quantity=1),
                DraftLine(model_hint="3706-50F", quantity=1),
                DraftLine(model_hint="3100H", quantity=50),
            ],
        )

    monkeypatch.setattr(bridge, "extract_sales_contract_draft", _capture_extract)
    monkeypatch.setattr(
        bridge,
        "resolve_draft_to_tool_slots",
        lambda *_a, **_k: {
            "customer_name": "惠州市丰驰家具有限公司",
            "products": [
                {"model_number": "MG", "quantity": "3"},
                {"model_number": "PU", "quantity": "2"},
                {"model_number": "308", "quantity": "1"},
                {"model_number": "3706-50F", "quantity": "1"},
                {"model_number": "3100H", "quantity": "50"},
            ],
        },
    )

    bad_args = {
        "customer_name": _FENGCHI_SMOKE_UTTERANCE.strip(),
        "products": [{"model_number": "", "quantity": "1"}],
    }
    out = merge_planner_sales_contract_args(dict(bad_args), _FENGCHI_SMOKE_UTTERANCE)
    assert captured == [_FENGCHI_SMOKE_UTTERANCE]
    assert out["customer_name"] == "惠州市丰驰家具有限公司"
    q = {p["model_number"]: int(p["quantity"]) for p in out["products"]}
    assert q == {"MG": 3, "PU": 2, "308": 1, "3706-50F": 1, "3100H": 50}
