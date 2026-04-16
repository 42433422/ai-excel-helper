"""
按购买单位（客户）批量写入 / 更新 products，并确保 purchase_units 存在。

供 ``POST /api/admin/products/bulk-import`` 与 Planner 工具 ``products_bulk_import`` 调用。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_NO_CODE_CHARS = frozenset({"—", "-", "－", "–", "\u2014", ""})
_MAX_ITEMS = 500


def _sql_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _norm_model(code: str, name: str, spec: str) -> str:
    c = (code or "").strip()
    if c and c not in _NO_CODE_CHARS:
        return c[:120]
    base = f"{(name or '').strip()}_{(spec or '').strip()}".strip("_")
    return re.sub(r"\s+", "", base)[:120] or "UNKNOWN"


def _parse_price(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(",", "")
    if not t:
        return 0.0
    m = re.search(r"[\d.]+", t)
    if not m:
        return 0.0
    try:
        return round(float(m.group()), 4)
    except ValueError:
        return 0.0


def _pg_purchase_unit_active_sql(column: str = "is_active") -> str:
    c = _sql_ident(column)
    return f"({c} IS NULL OR {c} = true OR CAST({c} AS INTEGER) = 1)"


def _meta_description(supplier_name: str, quote_date: str) -> str:
    parts: list[str] = []
    if supplier_name:
        parts.append(f"供应商:{supplier_name}")
    if quote_date:
        parts.append(f"报价日期:{quote_date}")
    return " | ".join(parts)[:2000]


def run_bulk_import(body: dict[str, Any]) -> dict[str, Any]:
    """
    body:
      - customer_name / unit_name: 购买单位（写入 products.unit）
      - items / products: [{ model_number?, name, specification?, price }]
      - replace: 为 true 时先删除该单位下全部产品再导入
      - dry_run: 仅统计不写库
      - supplier_name, quote_date: 可选，写入 description 前缀（若表有 description 列）
    """
    from sqlalchemy import inspect, text

    from backend.database import get_sync_engine
    from backend.shell.mod_row_scope import append_mod_scope_where, scoped_mod_id

    customer_name = str(
        body.get("customer_name") or body.get("unit_name") or ""
    ).strip()
    if not customer_name:
        return {
            "success": False,
            "error": "missing_customer_name",
            "message": "customer_name 不能为空",
        }

    raw_items = body.get("items") if body.get("items") is not None else body.get("products")
    if not isinstance(raw_items, list) or not raw_items:
        return {"success": False, "error": "empty_items", "message": "items 须为非空数组"}

    if len(raw_items) > _MAX_ITEMS:
        return {
            "success": False,
            "error": "too_many_items",
            "message": f"单次最多导入 {_MAX_ITEMS} 条",
        }

    replace = bool(body.get("replace"))
    dry_run = bool(body.get("dry_run"))
    supplier = str(body.get("supplier_name") or "").strip()
    quote_date = str(body.get("quote_date") or "").strip()
    meta = _meta_description(supplier, quote_date)

    try:
        eng = get_sync_engine()
    except Exception as e:
        logger.warning("bulk_import: no engine: %s", e)
        return {"success": False, "error": "no_database", "message": str(e)}

    insp = inspect(eng)
    tables = set(insp.get_table_names())
    if "products" not in tables:
        hint = (
            "当前 DATABASE_URL 所连的 PostgreSQL 库在默认 search_path 下没有 public.products。"
            "多为连到了空库/新库，或尚未执行 XCAGI 表结构初始化。"
            "请在本仓库执行 scripts/pg_init_xcagi_core.sql（或你环境中已有的 XCAGI 迁移），勿使用模型随意生成的列名。"
        )
        return {
            "success": False,
            "error": "no_products_table",
            "message": "数据库中不存在 products 表",
            "hint": hint,
            "schema_script": "scripts/pg_init_xcagi_core.sql",
        }
    if "purchase_units" not in tables:
        return {
            "success": False,
            "error": "no_purchase_units",
            "message": "数据库中不存在 purchase_units 表",
            "hint": (
                "purchase_units 为购买单位主表，且须含列 unit_name（非 name）。"
                "请执行 scripts/pg_init_xcagi_core.sql 或既有 XCAGI 迁移。"
            ),
            "schema_script": "scripts/pg_init_xcagi_core.sql",
        }

    pcols = {c["name"] for c in insp.get_columns("products")}
    if not {"model_number", "name"}.issubset(pcols):
        return {"success": False, "error": "bad_products_schema", "message": "products 表缺少 model_number 或 name"}

    pu_cols = {c["name"]: c for c in insp.get_columns("purchase_units")}
    if "unit_name" not in pu_cols:
        return {"success": False, "error": "bad_purchase_units", "message": "purchase_units 缺少 unit_name"}

    inserted = 0
    updated = 0
    deleted = 0
    errors: list[str] = []
    purchase_unit_created = False

    rows_in: list[tuple[str, str, str, float]] = []
    for i, row in enumerate(raw_items):
        if not isinstance(row, dict):
            errors.append(f"第{i + 1}行: 须为对象")
            continue
        name = str(row.get("name") or row.get("product_name") or "").strip()
        if not name:
            errors.append(f"第{i + 1}行: 缺少产品名称")
            continue
        code = str(row.get("model_number") or row.get("编号") or "").strip()
        spec = str(row.get("specification") or row.get("规格") or "").strip()
        price = _parse_price(row.get("price") or row.get("最新价格") or row.get("unit_price"))
        model = _norm_model(code, name, spec)
        rows_in.append((model, name, spec, price))

    if errors and not rows_in:
        return {
            "success": False,
            "error": "invalid_rows",
            "message": "无有效产品行",
            "errors": errors,
        }

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "customer_name": customer_name,
            "would_process": len(rows_in),
            "replace": replace,
            "errors": errors,
        }

    now = datetime.utcnow()
    act_sql = _pg_purchase_unit_active_sql()
    pu_cnames = set(pu_cols.keys())
    scope_mid = scoped_mod_id()

    with eng.begin() as conn:
        dup_parts = ["unit_name = :n", act_sql]
        dup_bind: dict[str, Any] = {"n": customer_name}
        append_mod_scope_where(dup_parts, dup_bind, pu_cnames)
        dup = conn.execute(
            text(f"SELECT id FROM purchase_units WHERE {' AND '.join(dup_parts)}"),
            dup_bind,
        ).first()
        if not dup:
            col_pairs: list[tuple[str, str]] = [
                ("unit_name", "un"),
                ("contact_person", "cp"),
                ("contact_phone", "ph"),
                ("address", "addr"),
            ]
            bind: dict[str, Any] = {
                "un": customer_name,
                "cp": "",
                "ph": "",
                "addr": "",
            }
            if "xcagi_mod_id" in pu_cnames and scope_mid:
                col_pairs.append(("xcagi_mod_id", "xmid"))
                bind["xmid"] = scope_mid
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
            conn.execute(
                text(f"INSERT INTO purchase_units ({cols_sql}) VALUES ({vals_sql})"),
                bind,
            )
            purchase_unit_created = True

        if replace:
            del_parts = ["btrim(cast(unit as text)) = btrim(cast(:u as text))"]
            del_bind: dict[str, Any] = {"u": customer_name}
            append_mod_scope_where(del_parts, del_bind, pcols)
            r = conn.execute(
                text("DELETE FROM products WHERE " + " AND ".join(del_parts)),
                del_bind,
            )
            deleted = int(r.rowcount or 0)

        active_cond = (
            "(is_active IS NULL OR CAST(is_active AS INTEGER) = 1)"
            if "is_active" in pcols
            else "true"
        )

        for model, name, spec, price in rows_in:
            try:
                if not replace:
                    fparts = [
                        "model_number = :m",
                        "btrim(cast(unit as text)) = btrim(cast(:u as text))",
                        active_cond,
                    ]
                    fbind: dict[str, Any] = {"m": model, "u": customer_name}
                    append_mod_scope_where(fparts, fbind, pcols)
                    found = conn.execute(
                        text(
                            "SELECT id FROM products WHERE "
                            + " AND ".join(fparts)
                            + " LIMIT 1"
                        ),
                        fbind,
                    ).first()
                    if found:
                        pid = int(found[0])
                        sets: list[str] = []
                        b: dict[str, Any] = {"id": pid}
                        if "name" in pcols:
                            sets.append(f"{_sql_ident('name')} = :name")
                            b["name"] = name
                        if "specification" in pcols:
                            sets.append(f"{_sql_ident('specification')} = :spec")
                            b["spec"] = spec
                        if "price" in pcols:
                            sets.append(f"{_sql_ident('price')} = :price")
                            b["price"] = price
                        if "brand" in pcols and supplier:
                            sets.append(f"{_sql_ident('brand')} = :brand")
                            b["brand"] = supplier
                        if "description" in pcols and meta:
                            sets.append(f"{_sql_ident('description')} = :desc")
                            b["desc"] = meta
                        if "updated_at" in pcols:
                            sets.append(f"{_sql_ident('updated_at')} = :ua")
                            b["ua"] = now
                        if sets:
                            conn.execute(
                                text(
                                    f"UPDATE products SET {', '.join(sets)} WHERE id = :id"
                                ),
                                b,
                            )
                            updated += 1
                        continue

                cols: list[str] = []
                vals: dict[str, Any] = {}
                cols.append("model_number")
                vals["model_number"] = model
                cols.append("name")
                vals["name"] = name
                if "specification" in pcols:
                    cols.append("specification")
                    vals["specification"] = spec
                if "price" in pcols:
                    cols.append("price")
                    vals["price"] = price
                if "unit" in pcols:
                    cols.append("unit")
                    vals["unit"] = customer_name
                if "quantity" in pcols:
                    cols.append("quantity")
                    vals["quantity"] = 0
                if "description" in pcols:
                    cols.append("description")
                    vals["description"] = meta
                elif meta and "description" not in pcols:
                    pass
                if "category" in pcols:
                    cols.append("category")
                    vals["category"] = ""
                if "brand" in pcols and supplier:
                    cols.append("brand")
                    vals["brand"] = supplier
                if "is_active" in pcols:
                    cols.append("is_active")
                    icol = next(c for c in insp.get_columns("products") if c["name"] == "is_active")
                    t = str(icol.get("type") or "").lower()
                    vals["is_active"] = True if "bool" in t else 1
                if "created_at" in pcols:
                    cols.append("created_at")
                    vals["created_at"] = now
                if "updated_at" in pcols:
                    cols.append("updated_at")
                    vals["updated_at"] = now
                if "xcagi_mod_id" in pcols and scope_mid:
                    cols.append("xcagi_mod_id")
                    vals["xcagi_mod_id"] = scope_mid

                cs = ", ".join(_sql_ident(c) for c in cols)
                ps = ", ".join(f":{c}" for c in cols)
                conn.execute(text(f"INSERT INTO products ({cs}) VALUES ({ps})"), vals)
                inserted += 1
            except Exception as e:
                logger.warning("bulk_import row failed model=%s: %s", model, e)
                errors.append(f"{model}: {e}")

    return {
        "success": True,
        "customer_name": customer_name,
        "inserted": inserted,
        "updated": updated,
        "deleted": deleted,
        "purchase_unit_created": purchase_unit_created,
        "replace": replace,
        "errors": errors,
    }
