"""product_db_read：PostgreSQL 上的统一读接口。"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect, text


@pytest.fixture()
def peninsula_product_seed():
    """插入唯一购买单位与产品，用例结束后删除。"""
    from backend.database import get_sync_engine

    suffix = uuid.uuid4().hex[:10]
    unit_name = f"半岛风情_{suffix}"
    eng = get_sync_engine()
    insp = inspect(eng)
    if "purchase_units" not in insp.get_table_names() or "products" not in insp.get_table_names():
        pytest.skip("当前 PostgreSQL 库缺少 purchase_units 或 products 表")

    pu_cols = {c["name"] for c in insp.get_columns("purchase_units")}
    if "unit_name" not in pu_cols:
        pytest.skip("purchase_units 缺少 unit_name")

    prod_cols = {c["name"] for c in insp.get_columns("products")}
    need = {"model_number", "name", "unit"}
    if not need.issubset(prod_cols):
        pytest.skip("products 表缺少 model_number/name/unit 等列")

    with eng.begin() as conn:
        if "is_active" in pu_cols:
            conn.execute(
                text(
                    "INSERT INTO purchase_units (unit_name, is_active) VALUES (:u, true)"
                ),
                {"u": unit_name},
            )
        else:
            conn.execute(
                text("INSERT INTO purchase_units (unit_name) VALUES (:u)"),
                {"u": unit_name},
            )

        cols_parts = ["model_number", "name", "unit", "price"]
        val_parts = [":mn", "'产品A'", ":u", "12.5"]
        params: dict = {"mn": f"m1_{suffix}", "u": unit_name}
        if "specification" in prod_cols:
            cols_parts.insert(2, "specification")
            val_parts.insert(2, "'规格1'")
        if "is_active" in prod_cols:
            cols_parts.append("is_active")
            t = str(
                next(c for c in insp.get_columns("products") if c["name"] == "is_active").get("type") or ""
            ).lower()
            val_parts.append("true" if "bool" in t else "1")
        cols_sql = ", ".join(cols_parts)
        vals_sql = ", ".join(val_parts)
        conn.execute(text(f"INSERT INTO products ({cols_sql}) VALUES ({vals_sql})"), params)

    yield unit_name

    with eng.begin() as conn:
        conn.execute(text("DELETE FROM products WHERE unit = :u"), {"u": unit_name})
        conn.execute(text("DELETE FROM purchase_units WHERE unit_name = :u"), {"u": unit_name})


def test_find_matching_customer_unified_exact(peninsula_product_seed):
    from backend.product_db_read import find_matching_customer_unified

    assert find_matching_customer_unified(peninsula_product_seed) == peninsula_product_seed


def test_load_products_for_price_list_by_customer(peninsula_product_seed):
    from backend.product_db_read import load_products_for_price_list_by_customer

    rows = load_products_for_price_list_by_customer(peninsula_product_seed, None)
    assert len(rows) == 1
    assert rows[0]["name"] == "产品A"
    assert float(rows[0]["price"]) == 12.5


def test_load_products_price_table_rows_exact_unit(peninsula_product_seed):
    from backend.product_db_read import load_products_price_table_rows

    rows = load_products_price_table_rows(peninsula_product_seed)
    assert len(rows) == 1
    assert rows[0].get("name") == "产品A"
