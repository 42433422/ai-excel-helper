"""
xcagi_compat 共享 DB 写入 / 更新 / 删除辅助函数。

供 xcagi_compat_customer / product 等路由子模块复用。
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy import inspect, text

from app.fastapi_routes.domains.db.base import (
    _customer_pg_engine_insp,
    _customer_pg_products_has_unit,
    _pg_expr_norm_unit,
    _pg_purchase_unit_active_sql,
    _sql_ident,
)
from app.fastapi_routes.domains.db.queries import (
    _customer_row_for_api,
)
from app.shell.mod_row_scope import (
    append_mod_scope_where,
    products_update_or_delete_mod_and,
    scoped_mod_id,
)
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


def _products_delete_by_unit_pg(eng, unit_name: str) -> int:
    un = (unit_name or "").strip()
    if not un:
        return 0
    insp = inspect(eng)
    if not _customer_pg_products_has_unit(insp):
        return 0
    pcols = {c["name"] for c in insp.get_columns("products")}
    col = _pg_expr_norm_unit("CAST(unit AS TEXT)")
    prm = _pg_expr_norm_unit("CAST(:u AS TEXT)")
    where_parts = [f"{col} = {prm}"]
    params: dict[str, object] = {"u": un}
    append_mod_scope_where(where_parts, params, pcols)
    where_sql = " AND ".join(where_parts)
    with eng.begin() as conn:
        r = conn.execute(
            text(f"DELETE FROM products WHERE {where_sql}"),
            params,
        )
        return int(r.rowcount or 0)


def _purchase_units_delete_by_norm_unit_pg(eng, unit_name: str) -> int:
    un = (unit_name or "").strip()
    if not un:
        return 0
    insp = inspect(eng)
    if "purchase_units" not in insp.get_table_names():
        return 0
    cols = {c["name"] for c in insp.get_columns("purchase_units")}
    if "unit_name" not in cols:
        return 0
    col = _pg_expr_norm_unit("CAST(unit_name AS TEXT)")
    prm = _pg_expr_norm_unit("CAST(:u AS TEXT)")
    where_parts = [f"{col} = {prm}"]
    params: dict[str, object] = {"u": un}
    append_mod_scope_where(where_parts, params, cols)
    where_sql = " AND ".join(where_parts)
    with eng.begin() as conn:
        r = conn.execute(
            text(f"DELETE FROM purchase_units WHERE {where_sql}"),
            params,
        )
        return int(r.rowcount or 0)


def _customers_delete_by_norm_name_pg(eng, insp, customer_name: str) -> int:
    cn = (customer_name or "").strip()
    if not cn or "customers" not in insp.get_table_names():
        return 0
    cols_names = {c["name"] for c in insp.get_columns("customers")}
    name_col = next(
        (c for c in ("customer_name", "name", "客户名称") if c in cols_names),
        None,
    )
    if not name_col:
        return 0
    col = _pg_expr_norm_unit(f"CAST({_sql_ident(name_col)} AS TEXT)")
    prm = _pg_expr_norm_unit("CAST(:u AS TEXT)")
    where_parts = [f"{col} = {prm}"]
    params: dict[str, object] = {"u": cn}
    append_mod_scope_where(where_parts, params, cols_names)
    where_sql = " AND ".join(where_parts)
    with eng.begin() as conn:
        r = conn.execute(
            text(f"DELETE FROM {_sql_ident('customers')} WHERE {where_sql}"),
            params,
        )
        return int(r.rowcount or 0)


def _purchase_units_delete_by_id_pg(eng, customer_id: int) -> int:
    insp = inspect(eng)
    if "purchase_units" not in insp.get_table_names():
        return 0
    cols = {c["name"] for c in insp.get_columns("purchase_units")}
    if "id" not in cols:
        return 0
    where_parts = ["id = :id"]
    params: dict[str, object] = {"id": int(customer_id)}
    append_mod_scope_where(where_parts, params, cols)
    where_sql = " AND ".join(where_parts)
    with eng.begin() as conn:
        r = conn.execute(
            text(f"DELETE FROM purchase_units WHERE {where_sql}"),
            params,
        )
        return int(r.rowcount or 0)


def _customers_delete_by_id_pg(eng, insp, customer_id: int) -> int:
    if "customers" not in insp.get_table_names():
        return 0
    cols = {c["name"] for c in insp.get_columns("customers")}
    id_col = "id" if "id" in cols else ("customer_id" if "customer_id" in cols else None)
    if not id_col:
        return 0
    where_parts = [f"{_sql_ident(id_col)} = :id"]
    params: dict[str, object] = {"id": int(customer_id)}
    append_mod_scope_where(where_parts, params, cols)
    where_sql = " AND ".join(where_parts)
    with eng.begin() as conn:
        r = conn.execute(
            text(f"DELETE FROM {_sql_ident('customers')} WHERE {where_sql}"),
            params,
        )
        return int(r.rowcount or 0)


def _products_unit_replace_pg(eng, old_name: str, new_name: str) -> None:
    o = (old_name or "").strip()
    n = (new_name or "").strip()
    if not o or not n or o == n:
        return
    insp = inspect(eng)
    if not _customer_pg_products_has_unit(insp):
        return
    pcols = {c["name"] for c in insp.get_columns("products")}
    col = _pg_expr_norm_unit("CAST(unit AS TEXT)")
    prm = _pg_expr_norm_unit("CAST(:oo AS TEXT)")
    where_parts = [f"{col} = {prm}"]
    params: dict[str, object] = {"nn": n, "oo": o}
    append_mod_scope_where(where_parts, params, pcols)
    where_sql = " AND ".join(where_parts)
    with eng.connect() as conn:
        conn.execute(
            text(f"UPDATE products SET unit = :nn WHERE {where_sql}"),
            params,
        )
        conn.commit()


def _customer_pg_row_select_sql(insp) -> tuple[str, list[str]]:
    have = {c["name"] for c in insp.get_columns("purchase_units")}
    want = [
        "id",
        "unit_name",
        "contact_person",
        "contact_phone",
        "address",
        "is_active",
        "created_at",
        "updated_at",
    ]
    sel = [c for c in want if c in have]
    if not sel or "id" not in sel:
        raise HTTPException(status_code=503, detail="purchase_units 表结构不完整（缺少 id）。")
    parts = []
    for c in sel:
        if c == "unit_name":
            parts.append(f"{_sql_ident(c)} AS unit_name")
        else:
            parts.append(_sql_ident(c))
    return ", ".join(parts), sel


def _customer_pg_fetch_by_id(eng, insp, customer_id: int) -> dict:
    sel_sql, _ = _customer_pg_row_select_sql(insp)
    pu_cols = {c["name"] for c in insp.get_columns("purchase_units")}
    where_parts = ["id = :id"]
    params: dict[str, object] = {"id": int(customer_id)}
    append_mod_scope_where(where_parts, params, pu_cols)
    where_sql = " AND ".join(where_parts)
    with eng.connect() as conn:
        r = (
            conn.execute(
                text(f"SELECT {sel_sql} FROM purchase_units WHERE {where_sql}"),
                params,
            )
            .mappings()
            .first()
        )
    if not r:
        raise HTTPException(status_code=404, detail="客户不存在")
    d = dict(r)
    d["customer_name"] = d.get("unit_name") or ""
    return _customer_row_for_api(d)


def _customer_pg_insert(name: str, cp: str, ph: str, addr: str) -> dict:
    eng, insp = _customer_pg_engine_insp()
    pu_cols = {c["name"]: c for c in insp.get_columns("purchase_units")}
    if "unit_name" not in pu_cols:
        raise HTTPException(status_code=503, detail="purchase_units 缺少 unit_name 列。")
    now = utc_now_naive()
    with eng.connect() as conn:
        dup_parts = ["unit_name = :n", _pg_purchase_unit_active_sql()]
        dup_bind: dict[str, object] = {"n": name}
        append_mod_scope_where(dup_parts, dup_bind, pu_cols)
        dup_sql = " AND ".join(dup_parts)
        dup = conn.execute(
            text(f"SELECT id FROM purchase_units WHERE {dup_sql}"),
            dup_bind,
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="客户名称已存在")
        col_pairs: list[tuple[str, str]] = [
            ("unit_name", "un"),
            ("contact_person", "cp"),
            ("contact_phone", "ph"),
            ("address", "addr"),
        ]
        bind: dict = {"un": name, "cp": cp, "ph": ph, "addr": addr}
        mid = scoped_mod_id()
        if "xcagi_mod_id" in pu_cols and mid:
            col_pairs.append(("xcagi_mod_id", "xmid"))
            bind["xmid"] = mid
        if "is_active" in pu_cols:
            col_pairs.append(("is_active", "ia"))
            t = str(pu_cols["is_active"].get("type") or "").lower()
            bind["ia"] = True if "bool" in t else 1
        if "created_at" in pu_cols:
            col_pairs.append(("created_at", "ca"))
            bind["ca"] = now
        if "updated_at" in pu_cols:
            col_pairs.append(("updated_at", "ua"))
            bind["ua"] = now
        cols_sql = ", ".join(_sql_ident(c) for c, _ in col_pairs)
        vals_sql = ", ".join(f":{bk}" for _, bk in col_pairs)
        r = conn.execute(
            text(f"INSERT INTO purchase_units ({cols_sql}) VALUES ({vals_sql}) RETURNING id"),
            bind,
        )
        new_id = int(r.scalar_one())
        conn.commit()
    return _customer_pg_fetch_by_id(eng, insp, new_id)


def _customer_pg_update(customer_id: int, name: str, cp: str, ph: str, addr: str) -> dict:
    eng, insp = _customer_pg_engine_insp()
    pu_cols = {c["name"] for c in insp.get_columns("purchase_units")}
    with eng.connect() as conn:
        prev_parts = ["id = :id", _pg_purchase_unit_active_sql()]
        prev_bind: dict[str, object] = {"id": int(customer_id)}
        append_mod_scope_where(prev_parts, prev_bind, pu_cols)
        prev = (
            conn.execute(
                text(f"SELECT id, unit_name FROM purchase_units WHERE {' AND '.join(prev_parts)}"),
                prev_bind,
            )
            .mappings()
            .first()
        )
        if not prev:
            raise HTTPException(status_code=404, detail="客户不存在或已删除")
        old_name = str(prev["unit_name"] or "").strip()
        clash_parts = [
            "unit_name = :n",
            "id != :id",
            _pg_purchase_unit_active_sql(),
        ]
        clash_bind: dict[str, object] = {"n": name, "id": int(customer_id)}
        append_mod_scope_where(clash_parts, clash_bind, pu_cols)
        clash = conn.execute(
            text(f"SELECT id FROM purchase_units WHERE {' AND '.join(clash_parts)}"),
            clash_bind,
        ).first()
        if clash:
            raise HTTPException(status_code=400, detail="客户名称与其他记录冲突")
        now = utc_now_naive()
        upd_bind = {
            "un": name,
            "cp": cp,
            "ph": ph,
            "addr": addr,
            "id": int(customer_id),
        }
        mod_and = products_update_or_delete_mod_and(pu_cols, upd_bind)
        if "updated_at" in pu_cols:
            upd_bind["ua"] = now
            conn.execute(
                text(
                    "UPDATE purchase_units SET unit_name = :un, contact_person = :cp, "
                    "contact_phone = :ph, address = :addr, updated_at = :ua WHERE id = :id"
                    + mod_and
                ),
                upd_bind,
            )
        else:
            conn.execute(
                text(
                    "UPDATE purchase_units SET unit_name = :un, contact_person = :cp, "
                    "contact_phone = :ph, address = :addr WHERE id = :id" + mod_and
                ),
                upd_bind,
            )
        conn.commit()
    if old_name and old_name != name.strip():
        _products_unit_replace_pg(eng, old_name, name.strip())
    return _customer_pg_fetch_by_id(eng, insp, customer_id)


def _customer_pg_select_customers_name_by_id(eng, insp, customer_id: int) -> tuple[str, str] | None:
    if "customers" not in insp.get_table_names():
        return None
    cols = {c["name"] for c in insp.get_columns("customers")}
    id_col = "id" if "id" in cols else ("customer_id" if "customer_id" in cols else None)
    name_col = next(
        (c for c in ("customer_name", "name", "客户名称") if c in cols),
        None,
    )
    if not id_col or not name_col:
        return None
    where_parts = [f"{_sql_ident(id_col)} = :id"]
    cbind: dict[str, object] = {"id": int(customer_id)}
    append_mod_scope_where(where_parts, cbind, cols)
    with eng.connect() as conn:
        r = (
            conn.execute(
                text(
                    f"SELECT {_sql_ident(name_col)} AS nm FROM {_sql_ident('customers')} "
                    f"WHERE {' AND '.join(where_parts)}"
                ),
                cbind,
            )
            .mappings()
            .first()
        )
        if not r:
            return None
        nm = str(r["nm"] or "").strip()
        return (nm, id_col)


def _customer_pg_delete_anywhere(customer_id: int) -> None:
    eng, insp = _customer_pg_engine_insp()
    cid = int(customer_id)
    resolved_name: str | None = None

    if "purchase_units" in insp.get_table_names():
        pu_cols = {c["name"] for c in insp.get_columns("purchase_units")}
        where_parts = ["id = :id"]
        pbind: dict[str, object] = {"id": cid}
        append_mod_scope_where(where_parts, pbind, pu_cols)
        with eng.connect() as conn:
            r = conn.execute(
                text(f"SELECT unit_name FROM purchase_units WHERE {' AND '.join(where_parts)}"),
                pbind,
            ).first()
            if r:
                resolved_name = str(r[0] or "").strip() or None

    if not resolved_name:
        csel = _customer_pg_select_customers_name_by_id(eng, insp, cid)
        if csel:
            nm, _id_col = csel
            resolved_name = (nm or "").strip() or None

    if not resolved_name:
        from app.fastapi_routes.domains.db.queries import _customer_find_by_id

        hint = _customer_find_by_id(cid)
        if hint and int(hint.get("id") or 0) == cid:
            resolved_name = str(hint.get("customer_name") or "").strip() or None

    n_prod = 0
    n_pu = 0
    n_cu = 0
    if resolved_name:
        n_prod += _products_delete_by_unit_pg(eng, resolved_name)
        n_pu += _purchase_units_delete_by_norm_unit_pg(eng, resolved_name)
        n_cu += _customers_delete_by_norm_name_pg(eng, insp, resolved_name)

    n_pu += _purchase_units_delete_by_id_pg(eng, cid)
    n_cu += _customers_delete_by_id_pg(eng, insp, cid)

    if n_prod == 0 and n_pu == 0 and n_cu == 0:
        raise HTTPException(status_code=404, detail="客户不存在")


def _customer_delete_unified(customer_id: int) -> None:
    _customer_pg_delete_anywhere(customer_id)
