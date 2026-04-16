"""customers_excel_import：表头解析等纯逻辑（不依赖 PostgreSQL）。"""

from __future__ import annotations

import pytest

from backend.customers_excel_import import resolve_customer_excel_columns


def test_resolve_columns_chinese_headers():
    cols = ["客户名称", "联系人", "电话", "地址"]
    m = resolve_customer_excel_columns(cols)
    assert m["customer_name_col"] == "客户名称"
    assert m["contact_person_col"] == "联系人"
    assert m["contact_phone_col"] == "电话"
    assert m["address_col"] == "地址"


def test_resolve_columns_unit_name_alias():
    m = resolve_customer_excel_columns(["购买单位", "contact_phone"])
    assert m["customer_name_col"] == "购买单位"
    assert m["contact_phone_col"] == "contact_phone"


def test_resolve_columns_first_wins_for_name():
    m = resolve_customer_excel_columns(["备注", "客户名称", "name"])
    assert m["customer_name_col"] == "客户名称"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  客户 名称  ", "客户名称"),
        ("Customer_Name", "customer_name"),
    ],
)
def test_norm_header_used_by_resolver(raw, expected):
    from backend.customers_excel_import import _norm_header

    assert _norm_header(raw) == expected
