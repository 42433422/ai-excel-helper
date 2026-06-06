"""
xcagi_compat 共享 DB 产品列表查询辅助函数。

从 db_queries 拆出，因 _load_products_list_impl_pg 较长。
"""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.fastapi_routes.domains.db.base import _EXPORT_MAX_ROWS
from app.infrastructure.db.sync_engine import get_sync_engine
from app.shell.mod_row_scope import append_mod_scope_where

logger = logging.getLogger(__name__)


def _load_products_list_impl_pg(
    page: int,
    per_page: int,
    keyword: str | None,
    unit: str | None,
) -> tuple[list[dict], int, str | None]:
    try:
        from app.shell.mod_business_scope import business_data_exposed, business_data_hidden_reason

        if not business_data_exposed():
            return [], 0, business_data_hidden_reason()
    except Exception:
        logger.debug("suppressed exception", exc_info=True)
    try:
        eng = get_sync_engine()
    except Exception as e:
        return [], 0, f"无法连接 PostgreSQL：{e}。请检查 DATABASE_URL 与数据库是否已启动。"

    try:
        with eng.connect() as conn:
            try:
                meta_timeout_ms = int(
                    (os.environ.get("FHD_PRODUCTS_META_TIMEOUT_MS") or "2000").strip()
                )
            except Exception:
                meta_timeout_ms = 2000
            try:
                if meta_timeout_ms > 0:
                    conn.execute(text(f"SET statement_timeout TO {meta_timeout_ms}"))
                insp = inspect(conn)
                table_names = set(insp.get_table_names())
                if "products" not in table_names:
                    return (
                        [],
                        0,
                        "当前库中不存在 public.products 表，产品列表为空。请在目标库执行仓库 scripts/pg_init_xcagi_core.sql 后重启后端。",
                    )
                col_names = {c["name"] for c in insp.get_columns("products")}
            except Exception as e:
                return (
                    [],
                    0,
                    f"products 元数据查询超时或失败：{e}。可调环境变量 FHD_PRODUCTS_META_TIMEOUT_MS。",
                )
            finally:
                if meta_timeout_ms > 0:
                    try:
                        conn.execute(text("SET statement_timeout TO 0"))
                    except Exception:
                        logger.debug("suppressed exception", exc_info=True)
        if not {"id", "model_number", "name"}.issubset(col_names):
            return (
                [],
                0,
                "products 表存在但缺少必要列（至少需要 id、model_number、name）。请对照 scripts/pg_init_xcagi_core.sql 修正表结构。",
            )

        where_parts: list[str] = []
        params: dict[str, object] = {}
        if "is_active" in col_names:
            where_parts.append("(is_active IS NULL OR CAST(is_active AS INTEGER) = 1)")
        kw = (keyword or "").strip()
        if kw:
            like = f"%{kw}%"
            or_parts: list[str] = []
            if "model_number" in col_names:
                or_parts.append("CAST(model_number AS TEXT) ILIKE :kw")
            if "name" in col_names:
                or_parts.append("CAST(name AS TEXT) ILIKE :kw")
            if "specification" in col_names:
                or_parts.append("CAST(specification AS TEXT) ILIKE :kw")
            if or_parts:
                where_parts.append("(" + " OR ".join(or_parts) + ")")
                params["kw"] = like
        un = (unit or "").strip()
        if un and "unit" in col_names:
            where_parts.append("unit = :uunit")
            params["uunit"] = un
        append_mod_scope_where(where_parts, params, col_names)
        where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        total: int | None = None
        count_sql = f"SELECT COUNT(*) FROM products{where_sql}"
        with eng.connect() as conn:
            try:
                timeout_ms = int(
                    (os.environ.get("FHD_PRODUCTS_COUNT_TIMEOUT_MS") or "1500").strip()
                )
            except Exception:
                timeout_ms = 1500
            try:
                if timeout_ms > 0:
                    conn.execute(text(f"SET statement_timeout TO {timeout_ms}"))
                total = int(conn.execute(text(count_sql), params).scalar_one())
            except Exception:
                total = None
            finally:
                if timeout_ms > 0:
                    try:
                        conn.execute(text("SET statement_timeout TO 0"))
                    except Exception:
                        logger.debug("suppressed exception", exc_info=True)

        sel: list[str] = ["id", "model_number", "name"]
        sel.append("specification" if "specification" in col_names else "NULL AS specification")
        sel.append("price" if "price" in col_names else "NULL AS price")
        sel.append("quantity" if "quantity" in col_names else "0 AS quantity")
        sel.append("description" if "description" in col_names else "NULL AS description")
        sel.append("category" if "category" in col_names else "NULL AS category")
        sel.append("brand" if "brand" in col_names else "NULL AS brand")
        sel.append("unit" if "unit" in col_names else "'' AS unit")
        sel.append("is_active" if "is_active" in col_names else "1 AS is_active")
        sel.append("created_at" if "created_at" in col_names else "NULL AS created_at")
        sel.append("updated_at" if "updated_at" in col_names else "NULL AS updated_at")

        offset = (page - 1) * per_page
        prefer_created_at = (
            os.environ.get("FHD_PRODUCTS_ORDER_BY_CREATED_AT") or ""
        ).strip() == "1"
        order = (
            "created_at DESC NULLS LAST, id DESC"
            if (prefer_created_at and "created_at" in col_names)
            else "id DESC"
        )
        data_sql = f"SELECT {', '.join(sel)} FROM products{where_sql} ORDER BY {order} LIMIT :lim OFFSET :off"
        qparams = {**params, "lim": per_page, "off": offset}
        rows: list[Any] = []
        data_query_err: Exception | None = None
        with eng.connect() as conn:
            try:
                query_timeout_ms = int(
                    (os.environ.get("FHD_PRODUCTS_QUERY_TIMEOUT_MS") or "8000").strip()
                )
            except Exception:
                query_timeout_ms = 8000
            try:
                if query_timeout_ms > 0:
                    conn.execute(text(f"SET statement_timeout TO {query_timeout_ms}"))
                rows = conn.execute(text(data_sql), qparams).mappings().all()
            except Exception as e:
                data_query_err = e
            finally:
                if query_timeout_ms > 0:
                    try:
                        conn.execute(text("SET statement_timeout TO 0"))
                    except Exception:
                        logger.debug("suppressed exception", exc_info=True)
        if data_query_err is not None:
            if total is None:
                total = 0
            return (
                [],
                total,
                "products 列表查询超时，已中断本次请求。请缩小筛选范围或稍后重试（可调环境变量 FHD_PRODUCTS_QUERY_TIMEOUT_MS）。",
            )

        rows_out: list[dict] = []
        for r in rows:
            d = dict(r)
            if d.get("price") is None:
                d["price"] = 0
            if d.get("quantity") is None:
                d["quantity"] = 0
            if d.get("unit") is None:
                d["unit"] = ""
            if d.get("is_active") is None:
                d["is_active"] = 1
            rows_out.append(d)
        if total is None:
            total = offset + len(rows_out)
        return rows_out, total, None
    except OperationalError as e:
        return (
            [],
            0,
            f"无法连接 PostgreSQL：{e}。请确认数据库已启动、DATABASE_URL 正确，"
            "并检查网络/VPN；若连接偏慢可增大环境变量 FHD_DB_CONNECT_TIMEOUT。",
        )


def _load_products_all_for_export(keyword: str | None, unit: str | None) -> list[dict]:
    rows, _, _hint = _load_products_list_impl_pg(1, _EXPORT_MAX_ROWS, keyword, unit)
    return rows
