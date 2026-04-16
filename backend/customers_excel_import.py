"""
客户 Excel → PostgreSQL ``customers``（可选同步 ``purchase_units``）。

供 ``POST /api/customers/import`` 使用：首行表头、首工作表；按客户名称去重后插入或更新。
"""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_MAX_FILE_BYTES = 20 * 1024 * 1024
_MAX_DATA_ROWS = 5000


def _sql_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _norm_header(s: str) -> str:
    t = str(s or "").strip()
    t = t.replace("\u3000", " ").replace("\xa0", " ")
    t = re.sub(r"\s+", "", t)
    return t.casefold()


# 归一化后的表头别名 → 语义字段
_NAME_HEADER_NORMS: frozenset[str] = frozenset(
    {
        _norm_header(x)
        for x in (
            "客户名称",
            "客户名",
            "客户",
            "customer_name",
            "customername",
            "name",
            "购买单位",
            "单位名称",
            "单位",
            "unit_name",
            "unitname",
        )
    }
)
_CP_HEADER_NORMS: frozenset[str] = frozenset(
    {_norm_header(x) for x in ("联系人", "contact_person", "contactperson", "联系人姓名")}
)
_PH_HEADER_NORMS: frozenset[str] = frozenset(
    {_norm_header(x) for x in ("电话", "手机", "联系电话", "contact_phone", "contactphone", "phone", "tel")}
)
_ADDR_HEADER_NORMS: frozenset[str] = frozenset(
    {_norm_header(x) for x in ("地址", "联系地址", "address", "contact_address", "contactaddress")}
)


def resolve_customer_excel_columns(columns: list[Any]) -> dict[str, str | None]:
    """
    根据 Excel 列名解析映射；每个语义最多绑定一列（先匹配者优先）。
    返回键：customer_name_col、contact_person_col、contact_phone_col、address_col。
    """
    out: dict[str, str | None] = {
        "customer_name_col": None,
        "contact_person_col": None,
        "contact_phone_col": None,
        "address_col": None,
    }
    for raw in columns:
        key = _norm_header(raw)
        if not key:
            continue
        if out["customer_name_col"] is None and key in _NAME_HEADER_NORMS:
            out["customer_name_col"] = str(raw)
        elif out["contact_person_col"] is None and key in _CP_HEADER_NORMS:
            out["contact_person_col"] = str(raw)
        elif out["contact_phone_col"] is None and key in _PH_HEADER_NORMS:
            out["contact_phone_col"] = str(raw)
        elif out["address_col"] is None and key in _ADDR_HEADER_NORMS:
            out["address_col"] = str(raw)
    return out


def _cell_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v != v:  # NaN
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "null"):
        return ""
    return s


def run_customers_excel_import_bytes(content: bytes) -> dict[str, Any]:
    """
    解析 xlsx/xls 字节流，写入 ``customers``；若存在 ``purchase_units`` 则按 ``unit_name`` upsert 同步联系方式。

    返回 dict：success、inserted、updated、skipped_blank、errors、synced_purchase_units
    """
    import pandas as pd
    from sqlalchemy import inspect, text

    from backend.database import get_sync_engine
    from backend.shell.mod_row_scope import (
        append_mod_scope_where,
        products_update_or_delete_mod_and,
        scoped_mod_id,
    )

    if not content:
        return {"success": False, "message": "空文件"}
    if len(content) > _MAX_FILE_BYTES:
        return {"success": False, "message": f"文件超过 {_MAX_FILE_BYTES // (1024 * 1024)}MB 上限"}

    try:
        eng = get_sync_engine()
    except Exception as e:
        logger.warning("customers excel import: no engine: %s", e)
        return {"success": False, "message": str(e), "error": "no_database"}

    insp = inspect(eng)
    tables = set(insp.get_table_names())
    if "customers" not in tables:
        return {
            "success": False,
            "error": "no_customers_table",
            "message": "当前库不存在 customers 表，无法导入客户。请执行 scripts/pg_init_xcagi_core.sql 后重试。",
            "schema_script": "scripts/pg_init_xcagi_core.sql",
        }
    if "purchase_units" not in tables:
        return {
            "success": False,
            "error": "no_purchase_units",
            "message": "当前库不存在 purchase_units 表，与现有客户写入校验一致。请执行 scripts/pg_init_xcagi_core.sql。",
            "schema_script": "scripts/pg_init_xcagi_core.sql",
        }

    cust_col_meta = {c["name"]: c for c in insp.get_columns("customers")}
    cust_cols = set(cust_col_meta)
    name_db = next(
        (c for c in ("customer_name", "name", "客户名称") if c in cust_cols),
        None,
    )
    if not name_db or "id" not in cust_cols:
        return {
            "success": False,
            "error": "bad_customers_schema",
            "message": "customers 表缺少必要列（至少需要 id 与客户名称列 customer_name / name）。",
        }
    cp_db = "contact_person" if "contact_person" in cust_cols else None
    ph_db = "contact_phone" if "contact_phone" in cust_cols else None
    addr_db = "address" if "address" in cust_cols else None
    has_ia = "is_active" in cust_cols
    has_ca = "created_at" in cust_cols
    has_ua = "updated_at" in cust_cols

    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, engine=None)
    except Exception as e:
        logger.info("customers excel import read_excel: %s", e)
        return {"success": False, "message": f"无法读取 Excel：{e}"}

    if df is None or df.empty:
        return {"success": False, "message": "工作表为空"}

    mapping = resolve_customer_excel_columns(list(df.columns))
    name_col = mapping["customer_name_col"]
    if not name_col:
        return {
            "success": False,
            "message": "未识别到客户名称列。首行请包含：客户名称 / 购买单位 / customer_name / unit_name 等之一。",
        }

    cp_col = mapping["contact_person_col"]
    ph_col = mapping["contact_phone_col"]
    addr_col = mapping["address_col"]

    # 同文件内后者覆盖前者：客户名称 → 行数据
    merged: dict[str, tuple[str, str, str]] = {}
    order_keys: list[str] = []
    skipped_blank = 0
    errors: list[str] = []

    for i, row in df.iterrows():
        if len(merged) >= _MAX_DATA_ROWS:
            errors.append(f"已超过单次最多 {_MAX_DATA_ROWS} 行，后续行已忽略")
            break
        name = _cell_str(row.get(name_col))
        if not name:
            skipped_blank += 1
            continue
        cp = _cell_str(row.get(cp_col)) if cp_col else ""
        ph = _cell_str(row.get(ph_col)) if ph_col else ""
        addr = _cell_str(row.get(addr_col)) if addr_col else ""
        if name not in merged:
            order_keys.append(name)
        merged[name] = (cp, ph, addr)

    if not merged:
        return {
            "success": False,
            "message": "没有有效的客户名称行（名称列全为空）。",
            "skipped_blank": skipped_blank,
        }

    now = datetime.utcnow()
    scope_mid = scoped_mod_id()
    inserted = 0
    updated = 0
    synced_pu = 0

    pu_cols = {c["name"]: c for c in insp.get_columns("purchase_units")}
    sync_pu = "unit_name" in pu_cols

    try:
        with eng.begin() as conn:
            for name in order_keys:
                cp, ph, addr = merged[name]
                sel_parts = [
                    f"lower(btrim(cast({_sql_ident(name_db)} as text))) = "
                    f"lower(btrim(cast(:n as text)))"
                ]
                sel_bind: dict[str, Any] = {"n": name}
                append_mod_scope_where(sel_parts, sel_bind, cust_cols)
                r = conn.execute(
                    text(
                        f"SELECT id FROM {_sql_ident('customers')} "
                        f"WHERE {' AND '.join(sel_parts)} LIMIT 1"
                    ),
                    sel_bind,
                ).first()
                if r:
                    cid = int(r[0])
                    sets: list[str] = []
                    bind: dict[str, Any] = {"id": cid, "n": name}
                    if cp_db:
                        sets.append(f"{_sql_ident(cp_db)} = :cp")
                        bind["cp"] = cp
                    if ph_db:
                        sets.append(f"{_sql_ident(ph_db)} = :ph")
                        bind["ph"] = ph
                    if addr_db:
                        sets.append(f"{_sql_ident(addr_db)} = :addr")
                        bind["addr"] = addr
                    if has_ua:
                        sets.append(f"{_sql_ident('updated_at')} = :ua")
                        bind["ua"] = now
                    if sets:
                        mod_and = products_update_or_delete_mod_and(cust_cols, bind)
                        conn.execute(
                            text(
                                f"UPDATE {_sql_ident('customers')} SET {', '.join(sets)} "
                                f"WHERE {_sql_ident('id')} = :id" + mod_and
                            ),
                            bind,
                        )
                    updated += 1
                else:
                    cols: list[str] = [name_db]
                    vals: list[str] = [":n"]
                    bind_i: dict[str, Any] = {"n": name}
                    if cp_db:
                        cols.append(cp_db)
                        vals.append(":cp")
                        bind_i["cp"] = cp
                    if ph_db:
                        cols.append(ph_db)
                        vals.append(":ph")
                        bind_i["ph"] = ph
                    if addr_db:
                        cols.append(addr_db)
                        vals.append(":addr")
                        bind_i["addr"] = addr
                    if has_ia:
                        cols.append("is_active")
                        t = str(cust_col_meta["is_active"].get("type") or "").lower()
                        bind_i["ia"] = True if "bool" in t else 1
                        vals.append(":ia")
                    if has_ca:
                        cols.append("created_at")
                        vals.append(":ca")
                        bind_i["ca"] = now
                    if has_ua:
                        cols.append("updated_at")
                        vals.append(":ua")
                        bind_i["ua"] = now
                    if "xcagi_mod_id" in cust_cols and scope_mid:
                        cols.append("xcagi_mod_id")
                        vals.append(":xmid")
                        bind_i["xmid"] = scope_mid
                    csql = ", ".join(_sql_ident(c) for c in cols)
                    vsql = ", ".join(vals)
                    conn.execute(
                        text(f"INSERT INTO {_sql_ident('customers')} ({csql}) VALUES ({vsql})"),
                        bind_i,
                    )
                    inserted += 1

                if sync_pu:
                    if _sync_purchase_unit_row(conn, pu_cols, name, cp, ph, addr, now):
                        synced_pu += 1
    except Exception as e:
        logger.exception("customers excel import transaction failed")
        return {"success": False, "message": f"写入数据库失败：{e}"}

    return {
        "success": True,
        "inserted": inserted,
        "updated": updated,
        "skipped_blank": skipped_blank,
        "synced_purchase_units": synced_pu,
        "errors": errors[:25],
        "total_distinct_names": len(merged),
    }


def _sync_purchase_unit_row(
    conn: Any,
    pu_cols: dict[str, Any],
    unit_name: str,
    cp: str,
    ph: str,
    addr: str,
    now: datetime,
) -> bool:
    """将购买单位与联系方式写入 ``purchase_units``（与产品报价单位一致）。成功返回 True。"""
    from sqlalchemy import text

    from backend.shell.mod_row_scope import append_mod_scope_where, scoped_mod_id

    pu_cnames = set(pu_cols.keys())
    dup_parts = ["unit_name = :n"]
    dup_b: dict[str, Any] = {"n": unit_name}
    append_mod_scope_where(dup_parts, dup_b, pu_cnames)
    dup = conn.execute(
        text(
            "SELECT id FROM purchase_units WHERE "
            + " AND ".join(dup_parts)
            + " ORDER BY id LIMIT 1"
        ),
        dup_b,
    ).first()
    if dup:
        sets = [
            "contact_person = :cp",
            "contact_phone = :ph",
            "address = :addr",
        ]
        bind: dict[str, Any] = {
            "cp": cp,
            "ph": ph,
            "addr": addr,
            "id": int(dup[0]),
        }
        if "is_active" in pu_cols:
            t = str(pu_cols["is_active"].get("type") or "").lower()
            sets.append(f"{_sql_ident('is_active')} = :ia")
            bind["ia"] = True if "bool" in t else 1
        if "updated_at" in pu_cols:
            sets.append("updated_at = :ua")
            bind["ua"] = now
        conn.execute(
            text(f"UPDATE purchase_units SET {', '.join(sets)} WHERE id = :id"),
            bind,
        )
        return True

    col_pairs: list[tuple[str, str]] = [
        ("unit_name", "un"),
        ("contact_person", "cp"),
        ("contact_phone", "ph"),
        ("address", "addr"),
    ]
    bind_i: dict[str, Any] = {"un": unit_name, "cp": cp, "ph": ph, "addr": addr}
    mid = scoped_mod_id()
    if "xcagi_mod_id" in pu_cnames and mid:
        col_pairs.append(("xcagi_mod_id", "xmid"))
        bind_i["xmid"] = mid
    if "is_active" in pu_cols:
        col_pairs.append(("is_active", "ia"))
        t = str(pu_cols["is_active"].get("type") or "").lower()
        bind_i["ia"] = True if "bool" in t else 1
    if "created_at" in pu_cols:
        col_pairs.append(("created_at", "ca"))
        bind_i["ca"] = now
    if "updated_at" in pu_cols:
        col_pairs.append(("updated_at", "ua"))
        bind_i["ua"] = now
    cols_sql = ", ".join(_sql_ident(c) for c, _ in col_pairs)
    vals_sql = ", ".join(f":{bk}" for _, bk in col_pairs)
    conn.execute(
        text(f"INSERT INTO purchase_units ({cols_sql}) VALUES ({vals_sql})"),
        bind_i,
    )
    return True
