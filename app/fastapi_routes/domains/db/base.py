"""
xcagi_compat 共享 DB 常量与 SQL 工具函数。

供 xcagi_compat_customer / product / … 等路由子模块复用，
避免循环依赖。
"""

from __future__ import annotations

import logging
import re

from fastapi import HTTPException, Request

from app.infrastructure.auth.db_token import verify_db_write_token_header
from app.infrastructure.db.sync_engine import get_sync_engine

logger = logging.getLogger(__name__)

_DEFAULT_INDUSTRY = {"id": "general", "name": "通用", "code": "general"}

_DEFAULT_MEASURE_UNITS: list[dict] = [
    {"id": 1, "name": "件", "symbol": "pcs"},
    {"id": 2, "name": "千克", "symbol": "kg"},
]

TRIVIAL_MEASURE_UNITS: frozenset[str] = frozenset(
    {
        "件",
        "个",
        "只",
        "箱",
        "盒",
        "包",
        "袋",
        "瓶",
        "桶",
        "罐",
        "千克",
        "公斤",
        "克",
        "斤",
        "两",
        "吨",
        "米",
        "厘米",
        "毫米",
        "千米",
        "升",
        "毫升",
        "套",
        "组",
        "台",
        "条",
        "张",
        "根",
        "卷",
        "块",
        "片",
        "支",
        "双",
        "对",
        "副",
        "把",
        "捆",
        "扎",
    }
)

_ALLOWED_SQL_TABLES = frozenset(
    {
        "customers",
        "products",
        "purchase_units",
        "templates",
        "template_usage_log",
        "shipment_orders",
        "users",
        "sessions",
        "wechat_contacts",
        "distillation_log",
        "extract_logs",
        "ai_action_audit",
        "mod_metadata",
        "mod_dependencies",
        "mod_ratings",
        "mod_statistics",
        "approval_requests",
    }
)

_ALLOWED_SQL_COLUMNS = frozenset(
    {
        "id",
        "name",
        "customer_name",
        "contact_person",
        "contact_phone",
        "address",
        "is_active",
        "created_at",
        "updated_at",
        "username",
        "display_name",
        "role",
        "email",
        "phone",
        "password",
        "specification",
        "price",
        "quantity",
        "description",
        "category",
        "brand",
        "unit",
        "unit_name",
        "nick_name",
        "remark",
    }
)

_EXPORT_MAX_ROWS = 50_000


def _sql_ident(name: str) -> str:
    if name.lower() in _ALLOWED_SQL_TABLES or name.lower() in _ALLOWED_SQL_COLUMNS:
        return '"' + name.replace('"', '""') + '"'
    return '"' + name.replace('"', '""') + '"'


def _validate_order_clause(order: str) -> str:
    tokens = [t.strip() for t in order.split(",")]
    validated = []
    for tok in tokens:
        m = re.match(r'^"?(\w+)"?\s+(ASC|DESC)(?:\s+NULLS\s+(?:FIRST|LAST))?$', tok, re.IGNORECASE)
        if not m:
            m2 = re.match(r'^"?(\w+)"?$', tok, re.IGNORECASE)
            if m2 and m2.group(1).lower() in _ALLOWED_SQL_COLUMNS:
                validated.append(_sql_ident(m2.group(1)))
                continue
            raise ValueError(f"invalid ORDER BY token: {tok!r}")
        col_name = m.group(1).lower()
        if col_name not in _ALLOWED_SQL_COLUMNS and col_name != "id":
            raise ValueError(f"ORDER BY column not allowed: {col_name!r}")
        direction = m.group(2).upper()
        suffix = tok[m.end(2) - len(m.group(2)) + len(m.group(2)) :]
        validated.append(f"{_sql_ident(m.group(1))} {direction}{suffix}")
    return ", ".join(validated)


def _insp_table_exists(insp, table_name: str) -> bool:
    ht = getattr(insp, "has_table", None)
    if callable(ht):
        try:
            return bool(ht(table_name))
        except Exception:
            logger.debug("suppressed exception", exc_info=True)
    try:
        return table_name in insp.get_table_names()
    except Exception:
        return False


def _exc_chain_has_undefined_table(e: BaseException) -> bool:
    cur: BaseException | None = e
    for _ in range(20):
        if cur is None:
            break
        if cur.__class__.__name__ == "UndefinedTable":
            return True
        cur = cur.__cause__ or getattr(cur, "orig", None)
    return False


def _pg_purchase_unit_active_sql(column: str = "is_active") -> str:
    c = _sql_ident(column)
    return f"({c} IS NULL OR {c} = true OR CAST({c} AS INTEGER) = 1)"


def _customer_pg_engine_insp():
    from sqlalchemy import inspect as _insp

    eng = get_sync_engine()
    return eng, _insp(eng)


def _customer_pg_products_has_unit(insp) -> bool:
    if "products" not in insp.get_table_names():
        return False
    return "unit" in {c["name"] for c in insp.get_columns("products")}


def _pg_expr_norm_unit(column_sql: str) -> str:
    return (
        f"lower(btrim(replace(replace(replace(coalesce({column_sql}, ''), CHR(12288), ' '), "
        f"CHR(160), ' '), CHR(9), ' ')))"
    )


def _product_parse_id(raw: object) -> int | None:
    if raw is None or raw is False:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    try:
        n = int(str(raw).strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _product_parse_quantity(raw: object) -> int:
    if raw is None or raw == "":
        return 0
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return 0


def _product_parse_is_active(raw: object) -> bool | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return int(raw) != 0
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return None


def _business_mod_json_block() -> dict | None:
    try:
        from app.shell.mod_business_scope import business_data_exposed, business_data_hidden_reason

        if business_data_exposed():
            return None
        return {
            "success": False,
            "message": business_data_hidden_reason() or "扩展 Mod 未就绪，业务接口已关闭。",
        }
    except Exception:
        return None


def _customers_write_raise(request: Request) -> None:
    verify_db_write_token_header(request)
    try:
        from sqlalchemy import inspect as _insp

        eng = get_sync_engine()
        insp = _insp(eng)
        if "purchase_units" not in insp.get_table_names():
            raise HTTPException(
                status_code=503,
                detail="PostgreSQL 库中缺少 purchase_units 表，无法写入客户。",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"无法校验 PostgreSQL 库结构: {e}",
        ) from e


def _products_write_raise(request: Request) -> None:
    verify_db_write_token_header(request)
    try:
        from sqlalchemy import inspect as _insp

        eng = get_sync_engine()
        insp = _insp(eng)
        if "products" not in insp.get_table_names():
            raise HTTPException(
                status_code=503,
                detail="PostgreSQL 库中缺少 products 表，无法写入产品。",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"无法校验 PostgreSQL 库结构: {e}",
        ) from e


def _customer_body_name_contact(body: dict) -> tuple[str, str, str, str]:
    name = body.get("customer_name") or body.get("name") or body.get("unit_name") or ""
    name = str(name).strip()
    cp = str(body.get("contact_person") or "").strip()
    ph = str(body.get("contact_phone") or "").strip()
    addr = str(body.get("contact_address") or body.get("address") or "").strip()
    return name, cp, ph, addr
