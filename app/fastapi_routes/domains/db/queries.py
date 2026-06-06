"""
xcagi_compat 共享 DB 查询辅助函数。

供 xcagi_compat_customer / product 等路由子模块复用。
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.fastapi_routes.domains.db.base import (
    TRIVIAL_MEASURE_UNITS,
    _exc_chain_has_undefined_table,
    _insp_table_exists,
    _sql_ident,
)
from app.infrastructure.db.sync_engine import get_sync_engine
from app.shell.mod_row_scope import append_mod_scope_where

logger = logging.getLogger(__name__)


def _load_purchase_units_rows_pg() -> list[dict]:
    try:
        from app.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return []
    except Exception:
        logger.debug("suppressed exception", exc_info=True)
    try:
        eng = get_sync_engine()
        insp = inspect(eng)
    except Exception as e:
        logger.warning("purchase_units pg: no engine (%s)", e)
        return []
    if not _insp_table_exists(insp, "purchase_units"):
        return []
    pu_cols = {c["name"] for c in insp.get_columns("purchase_units")}
    where_parts: list[str] = []
    bind: dict[str, object] = {}
    append_mod_scope_where(where_parts, bind, pu_cols)
    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    try:
        with eng.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        f"""
                    SELECT id, unit_name, contact_person, contact_phone, address, is_active
                    FROM purchase_units
                    {where_sql}
                    ORDER BY unit_name
                    """
                    ),
                    bind,
                )
                .mappings()
                .all()
            )
    except Exception as e:
        if _exc_chain_has_undefined_table(e):
            logger.debug("purchase_units pg: relation missing at query time (%s)", e)
        else:
            logger.warning("purchase_units pg: query failed: %s", e)
        return []
    out: list[dict] = []
    for r in rows:
        ia = r.get("is_active")
        if ia in (0, False, "0", "false", "f", "F"):
            continue
        out.append(dict(r))
    return out


def _load_purchase_units_rows() -> list[dict]:
    return _load_purchase_units_rows_pg()


def _distinct_units_from_products_db_pg() -> list[dict]:
    try:
        from app.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return []
    except Exception:
        logger.debug("suppressed exception", exc_info=True)
    try:
        eng = get_sync_engine()
    except Exception:
        return []
    try:
        insp = inspect(eng)
        if "products" not in insp.get_table_names():
            return []
        col_names = {c["name"] for c in insp.get_columns("products")}
        if "unit" not in col_names:
            return []
        where_parts = ["unit IS NOT NULL AND TRIM(unit) != ''"]
        if "is_active" in col_names:
            where_parts.append("(is_active IS NULL OR CAST(is_active AS INTEGER) = 1)")
        bind: dict[str, object] = {}
        append_mod_scope_where(where_parts, bind, col_names)
        where_sql = "WHERE " + " AND ".join(where_parts)
        with eng.connect() as conn:
            rows = conn.execute(
                text(f"SELECT DISTINCT unit FROM products {where_sql} ORDER BY unit"),
                bind,
            ).fetchall()
        names = [str(row[0]).strip() for row in rows if row[0] is not None]
        return [{"id": i + 1, "name": u, "symbol": u} for i, u in enumerate(names)]
    except OperationalError:
        return []
    except Exception as e:
        logger.warning("distinct product units pg: %s", e)
        return []


def _distinct_units_from_products_db() -> list[dict]:
    return _distinct_units_from_products_db_pg()


def _merged_purchase_unit_entries() -> list[dict]:
    rows = _load_purchase_units_rows()
    seen = {
        str(r.get("unit_name") or "").strip().lower()
        for r in rows
        if str(r.get("unit_name") or "").strip()
    }
    out: list[dict] = [dict(r) for r in rows]
    distinct = _distinct_units_from_products_db()
    max_id = 0
    for r in out:
        rid = r.get("id")
        if isinstance(rid, int):
            max_id = max(max_id, rid)
    syn = 0
    for d in distinct:
        name = str(d.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        if name in TRIVIAL_MEASURE_UNITS:
            continue
        seen.add(key)
        syn += 1
        out.append(
            {
                "id": max_id + syn,
                "unit_name": name,
                "contact_person": "",
                "contact_phone": "",
                "address": "",
                "is_active": 1,
            }
        )
    return out


def _customer_rows_from_merged_unit_entries() -> list[dict]:
    out: list[dict] = []
    for r in _merged_purchase_unit_entries():
        name = str(r.get("unit_name") or "").strip()
        if not name:
            continue
        rid = r.get("id")
        oid = rid if isinstance(rid, int) else len(out) + 1
        out.append(
            {
                "id": oid,
                "customer_name": name,
                "contact_person": str(r.get("contact_person") or ""),
                "contact_phone": str(r.get("contact_phone") or ""),
                "address": str(r.get("address") or ""),
                "is_active": int(r.get("is_active") or 1),
            }
        )
    return out


def _load_customers_pg_from_customers_table(eng, insp) -> list[dict]:
    cols = {c["name"] for c in insp.get_columns("customers")}
    id_col = "id" if "id" in cols else ("customer_id" if "customer_id" in cols else None)
    name_col = next(
        (c for c in ("customer_name", "name", "客户名称") if c in cols),
        None,
    )
    if not id_col or not name_col:
        return []
    sel = [
        f"{_sql_ident(id_col)} AS id",
        f"{_sql_ident(name_col)} AS customer_name",
    ]
    cp = next((c for c in ("contact_person", "联系人") if c in cols), None)
    if cp:
        sel.append(f"{_sql_ident(cp)} AS contact_person")
    ph = next((c for c in ("contact_phone", "phone", "电话") if c in cols), None)
    if ph:
        sel.append(f"{_sql_ident(ph)} AS contact_phone")
    ad = next((c for c in ("address", "地址") if c in cols), None)
    if ad:
        sel.append(f"{_sql_ident(ad)} AS address")
    if "is_active" in cols:
        sel.append(_sql_ident("is_active") + " AS is_active")
    where_parts: list[str] = []
    bind: dict[str, object] = {}
    if "is_active" in cols:
        where_parts.append(
            "("
            + _sql_ident("is_active")
            + " IS NULL OR "
            + _sql_ident("is_active")
            + " = true OR CAST("
            + _sql_ident("is_active")
            + " AS INTEGER) = 1)"
        )
    append_mod_scope_where(where_parts, bind, cols)
    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    order = f"{_sql_ident(name_col)}, {_sql_ident(id_col)}"
    sql = f"SELECT {', '.join(sel)} FROM {_sql_ident('customers')}{where_sql} ORDER BY {order}"
    try:
        with eng.connect() as conn:
            rows = conn.execute(text(sql), bind).mappings().all()
    except Exception as e:
        logger.warning("customers pg customers table: %s", e)
        return []
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        if "is_active" not in d:
            d["is_active"] = 1
        out.append(d)
    return out


def _load_customers_pg_from_purchase_units(eng) -> list[dict]:
    try:
        insp = inspect(eng)
        pu_cols = {c["name"] for c in insp.get_columns("purchase_units")}
        where_parts: list[str] = []
        bind: dict[str, object] = {}
        append_mod_scope_where(where_parts, bind, pu_cols)
        where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        with eng.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        f"""
                    SELECT id, unit_name, contact_person, contact_phone, address, is_active
                    FROM purchase_units
                    {where_sql}
                    ORDER BY unit_name
                    """
                    ),
                    bind,
                )
                .mappings()
                .all()
            )
    except Exception as e:
        logger.warning("customers pg purchase_units: %s", e)
        return []
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        ia = d.get("is_active")
        if ia in (0, False, "0", "false", "f", "F"):
            continue
        d["customer_name"] = (d.pop("unit_name", None) or "") or ""
        out.append(d)
    return out


def _load_customers_rows_pg() -> list[dict]:
    try:
        eng = get_sync_engine()
        insp = inspect(eng)
    except Exception as e:
        logger.warning("customers pg: no engine (%s)", e)
        return []
    names = set(insp.get_table_names())
    if "customers" in names:
        rows = _load_customers_pg_from_customers_table(eng, insp)
        if rows:
            return rows
    if "purchase_units" in names:
        return _load_customers_pg_from_purchase_units(eng)
    return []


def _load_customers_rows() -> list[dict]:
    try:
        from app.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return []
    except Exception:
        logger.debug("suppressed exception", exc_info=True)
    rows = _load_customers_rows_pg()
    if rows:
        return rows
    return _customer_rows_from_merged_unit_entries()


def _customer_row_for_api(row: dict) -> dict:
    cn = (row.get("customer_name") or row.get("unit_name") or row.get("name") or "").strip()
    return {
        "id": row["id"],
        "name": cn,
        "customer_name": cn,
        "contact_person": row.get("contact_person") or "",
        "contact_phone": row.get("contact_phone") or "",
        "contact_address": row.get("address") or row.get("contact_address") or "",
        "address": row.get("address") or "",
        "is_active": int(row.get("is_active") or 1),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _customer_row_matches_keyword(row: dict, keyword: str) -> bool:
    k = (keyword or "").strip().lower()
    if not k:
        return True
    for key in (
        "customer_name",
        "name",
        "unit_name",
        "contact_person",
        "contact_phone",
        "phone",
        "company",
        "address",
        "contact_address",
    ):
        v = row.get(key)
        if v is None:
            continue
        if k in str(v).lower():
            return True
    return False


def _customer_find_by_id(customer_id: int) -> dict | None:
    for row in _load_customers_rows():
        if int(row.get("id") or 0) == int(customer_id):
            return dict(row)
    return None


def _customers_schema_hint_if_empty() -> str | None:
    try:
        eng = get_sync_engine()
        names = set(inspect(eng).get_table_names())
    except Exception as e:
        return f"无法连接 PostgreSQL：{e}。请检查 DATABASE_URL。"

    has_c = "customers" in names
    has_pu = "purchase_units" in names
    has_p = "products" in names
    if not has_c and not has_pu:
        return (
            "当前库缺少 customers 与 purchase_units 表，无法展示客户。请执行 scripts/pg_init_xcagi_core.sql "
            "（会创建 purchase_units / products；可选 customers）。"
        )
    if not has_pu and has_p:
        return (
            "当前库缺少 purchase_units；客户页将仅从 customers 或 products.unit 推断。"
            "建议执行 scripts/pg_init_xcagi_core.sql 补齐 purchase_units。"
        )
    if not has_p and not has_c:
        return "当前库缺少 customers 与 products 表，客户与产品数据均为空。请执行 scripts/pg_init_xcagi_core.sql。"
    return None


def _units_select_data_unified() -> list[dict]:
    rows = _load_customers_rows()
    seen: set[str] = set()
    staged: list[tuple[str, int | None]] = []
    for row in rows:
        name = str(row.get("customer_name") or row.get("name") or "").strip()
        if not name:
            continue
        lk = name.lower()
        if lk in seen:
            continue
        seen.add(lk)
        rid = row.get("id")
        try:
            oid = int(rid)
        except (TypeError, ValueError):
            oid = None
        staged.append((name, oid))

    out: list[dict] = []
    max_id = 0
    for _, oid in staged:
        if oid is not None:
            max_id = max(max_id, oid)
    next_id = max_id
    for name, oid in staged:
        if oid is not None:
            out.append({"id": oid, "name": name, "symbol": name})
        else:
            next_id += 1
            out.append({"id": next_id, "name": name, "symbol": name})
            max_id = next_id

    distinct = _distinct_units_from_products_db()
    syn = 0
    for d in distinct:
        name = str(d.get("name") or "").strip()
        if not name:
            continue
        lk = name.lower()
        if lk in seen:
            continue
        if name in TRIVIAL_MEASURE_UNITS:
            continue
        seen.add(lk)
        syn += 1
        out.append({"id": max_id + syn, "name": name, "symbol": name})
    return out


def _products_units_for_select() -> dict:
    data = _units_select_data_unified()
    if data:
        return {"success": True, "data": data}
    distinct = _distinct_units_from_products_db()
    if distinct:
        return {"success": True, "data": distinct}
    return {"success": True, "data": []}
