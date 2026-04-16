"""
统一从 PostgreSQL 主库读取产品与购买单位，供模板、价格表、工具链使用。
不包含微信相关数据源。
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from backend.database import get_sync_engine
from backend.shell.mod_row_scope import append_mod_scope_where

logger = logging.getLogger(__name__)


def _pg_active_products_clause(col: str = "is_active") -> str:
    """兼容 ``is_active`` 为 BOOLEAN 或 INTEGER（以及可安全转为整型的列）：避免 ``integer = true`` 报错。"""
    c = '"' + col.replace('"', '""') + '"'
    return f"({c} IS NULL OR CAST({c} AS INTEGER) = 1)"


def _pg_active_purchase_units_clause(col: str = "is_active") -> str:
    return _pg_active_products_clause(col)


def _compact(s: str) -> str:
    return "".join((s or "").split())


def find_matching_customer_unified(input_name: str) -> str | None:
    """从 purchase_units 按名称模糊匹配客户（与旧 shared_utils 行为一致）。"""
    try:
        from backend.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return None
    except Exception:
        pass

    input_clean = (input_name or "").strip()
    if not input_clean:
        return None

    try:
        from sqlalchemy import inspect, text

        eng = get_sync_engine()
        inspector = inspect(eng)
        if "purchase_units" not in inspector.get_table_names():
            return None
        w_parts = [_pg_active_purchase_units_clause()]
        bind: dict[str, object] = {}
        pu_cols = {c["name"] for c in inspector.get_columns("purchase_units")}
        append_mod_scope_where(w_parts, bind, pu_cols)
        w_sql = " AND ".join(w_parts)
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, unit_name FROM purchase_units
                    WHERE {w_sql}
                    ORDER BY unit_name
                    """
                ),
                bind,
            ).fetchall()
    except Exception as e:
        logger.warning("find_matching_customer_unified pg: %s", e)
        return None

    names = [str(cust_name).strip() for _, cust_name in rows if cust_name]
    if not names:
        return None

    # 与生成合同一致：先从整句中抽取公司片段，再对库名做子串命中（避免整句 Jaccard 被稀释）
    try:
        from backend.shared_utils import extract_customer_name

        narrowed = extract_customer_name(input_clean) or ""
    except Exception:
        narrowed = ""
    candidates: list[str] = []
    for c in (narrowed.strip(), input_clean):
        if c and c not in candidates:
            candidates.append(c)
    # 常见笔误：「丰驰」↔「枫驰」（惠州客户简称）
    extra: list[str] = []
    for c in list(candidates):
        if "丰驰" in c and "枫驰" not in c:
            t = c.replace("丰驰", "枫驰", 1)
            if t and t not in candidates and t not in extra:
                extra.append(t)
    candidates.extend(extra)

    for cand in candidates:
        for cn in names:
            if cn == cand:
                return cn

    def _substring_hit(cand: str) -> str | None:
        ac = _compact(cand)
        if len(ac) < 6:
            return None
        best_cn: str | None = None
        best_len = 0
        for cn in names:
            bc = _compact(cn)
            if ac in bc or bc in ac:
                if len(bc) > best_len:
                    best_len = len(bc)
                    best_cn = cn
        return best_cn

    for cand in candidates:
        hit = _substring_hit(cand)
        if hit:
            logger.info("子串匹配客户：'%s' -> '%s'", cand, hit)
            return hit

    # BGE 向量语义：整句/抽取片段与购买单位名称对齐（与产品语义模块同源）
    allowed = frozenset(names)
    _sem_off = os.environ.get("FHD_DISABLE_CUSTOMER_SEMANTIC", "").strip().lower() in ("1", "true", "yes")
    _sem_win_default_off = sys.platform == "win32" and os.environ.get(
        "FHD_ENABLE_CUSTOMER_SEMANTIC", ""
    ).strip().lower() not in ("1", "true", "yes")
    if _sem_off or _sem_win_default_off:
        if _sem_win_default_off and not _sem_off:
            logger.debug(
                "Windows：默认跳过客户名 BGE 语义匹配（避免 torch 弹窗/告警）；"
                "需要语义时设置环境变量 FHD_ENABLE_CUSTOMER_SEMANTIC=1"
            )
    else:
        try:
            from backend.customer_semantic_matcher import try_semantic_customer_pick

            qlist = [c for c in candidates if c]
            sem_hit = try_semantic_customer_pick(qlist, unit_names=names, allowed=allowed)
            if sem_hit:
                return sem_hit
        except Exception as e:
            logger.debug("customer semantic match skipped: %s", e)

    best_match = None
    best_score = 0.0
    for cust_id, cust_name in rows:
        if not cust_name:
            continue
        cn = str(cust_name).strip()
        if cn == input_clean:
            return cn
        score = _calculate_similarity(input_clean, cn)
        if score > best_score and score > 0.6:
            best_score = score
            best_match = cn
    if best_match:
        logger.info("模糊匹配客户：'%s' -> '%s' (score=%.2f)", input_clean, best_match, best_score)
    return best_match


def _calculate_similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    a, b = set(s1), set(s2)
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / union


def load_purchase_units_for_templates() -> dict[str, dict[str, Any]]:
    """
    返回 unit_name -> {id, unit_name, contact_person, contact_phone}，
    与 excel_template._load_units_from_db / word_template 结构一致。
    """
    out: dict[str, dict[str, Any]] = {}
    try:
        from backend.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return out
    except Exception:
        pass
    try:
        from sqlalchemy import inspect, text

        eng = get_sync_engine()
        inspector = inspect(eng)
        if "purchase_units" not in inspector.get_table_names():
            return out
        pu_cols = {c["name"] for c in inspector.get_columns("purchase_units")}
        w_parts = [_pg_active_purchase_units_clause()]
        bind: dict[str, object] = {}
        append_mod_scope_where(w_parts, bind, pu_cols)
        w_sql = " AND ".join(w_parts)
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, unit_name, contact_person, contact_phone
                    FROM purchase_units
                    WHERE {w_sql}
                    """
                ),
                bind,
            ).fetchall()
        for row in rows:
            un = str(row[1] or "").strip()
            if not un:
                continue
            out[un] = {
                "id": row[0],
                "unit_name": un,
                "contact_person": row[2],
                "contact_phone": row[3],
            }
    except Exception as e:
        logger.warning("load_purchase_units_for_templates pg: %s", e)
    return out


def load_products_dict_for_templates() -> dict[str, dict[str, Any]]:
    """
    返回 name.strip() -> {id, name, model_number, specification, price}，
    与 excel_template._load_products_from_db 的 dict 结构一致。
    """
    out: dict[str, dict[str, Any]] = {}
    try:
        from backend.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return out
    except Exception:
        pass
    try:
        from sqlalchemy import inspect, text

        eng = get_sync_engine()
        inspector = inspect(eng)
        if "products" not in inspector.get_table_names():
            return out
        cols = {c["name"] for c in inspector.get_columns("products")}
        if not {"id", "name"}.issubset(cols):
            return out
        w_parts = [_pg_active_products_clause() if "is_active" in cols else "true"]
        bind: dict[str, object] = {}
        append_mod_scope_where(w_parts, bind, cols)
        w_sql = " AND ".join(w_parts)
        sel_sql = ", ".join(
            [
                "id",
                "name",
                "model_number" if "model_number" in cols else "CAST(NULL AS TEXT) AS model_number",
                "specification"
                if "specification" in cols
                else "CAST(NULL AS TEXT) AS specification",
                "price" if "price" in cols else "CAST(NULL AS DOUBLE PRECISION) AS price",
            ]
        )
        with eng.connect() as conn:
            rows = conn.execute(
                text(f"SELECT {sel_sql} FROM products WHERE {w_sql}"),
                bind,
            ).fetchall()
        for row in rows:
            name = str(row[1] or "").strip()
            if not name:
                continue
            out[name] = {
                "id": row[0],
                "name": row[1],
                "model_number": row[2],
                "specification": row[3],
                "price": row[4],
            }
    except Exception as e:
        logger.warning("load_products_dict_for_templates pg: %s", e)
    return out


def load_products_for_price_list_by_customer(
    customer_name: str,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    """
    按客户（products.unit）加载产品列表；keyword 时按名称/型号/规格模糊匹配。
    供 tools._load_products_for_price_list 与 price_list 使用。
    """
    try:
        from backend.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return []
    except Exception:
        pass

    cn = (customer_name or "").strip()
    if not cn:
        return []
    kw = (keyword or "").strip()

    try:
        from sqlalchemy import inspect, text

        eng = get_sync_engine()
        inspector = inspect(eng)
        if "products" not in inspector.get_table_names():
            return []
        col_names = {c["name"] for c in inspector.get_columns("products")}
        if "unit" not in col_names:
            return []
        where = [_pg_active_products_clause(), "unit = :u"]
        params: dict[str, Any] = {"u": cn}
        if kw and {"name", "model_number", "specification"}.intersection(col_names):
            like = f"%{kw}%"
            ors = []
            if "name" in col_names:
                ors.append("CAST(name AS TEXT) ILIKE :kw")
            if "model_number" in col_names:
                ors.append("CAST(model_number AS TEXT) ILIKE :kw")
            if "specification" in col_names:
                ors.append("CAST(specification AS TEXT) ILIKE :kw")
            if ors:
                where.append("(" + " OR ".join(ors) + ")")
                params["kw"] = like
        append_mod_scope_where(where, params, col_names)
        where_sql = " AND ".join(where)
        sql = (
            f"SELECT name, model_number, specification, price FROM products "
            f"WHERE {where_sql} ORDER BY name"
        )
        with eng.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        return [
            {
                "name": str(r[0] or ""),
                "model_number": str(r[1] or ""),
                "specification": str(r[2] or ""),
                "price": r[3] or 0,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("load_products_for_price_list_by_customer pg: %s", e)
        return []


def load_products_price_table_rows(customer_name: str) -> list[dict[str, Any]]:
    """
    价格表 API：按客户 unit 精确筛选活跃产品（与旧 price_list._load_products_from_db 字段对齐）。
    """
    from backend.shared_utils import extract_customer_name  # 延迟导入避免循环依赖

    extracted = extract_customer_name(customer_name)
    if extracted:
        matched = find_matching_customer_unified(extracted)
    else:
        matched = find_matching_customer_unified(customer_name)
    cn = matched or (customer_name or "").strip()
    if matched:
        logger.info("价格表加载：模糊匹配到客户：%s", cn)

    rows = load_products_for_price_list_by_customer(cn, keyword=None)
    products: list[dict[str, Any]] = []
    for r in rows:
        products.append(
            {
                "model_number": str(r.get("model_number") or "").strip(),
                "name": str(r.get("name") or "").strip(),
                "specification": str(r.get("specification") or "").strip(),
                "unit": str(cn or "").strip() or "桶",
                "price": float(r.get("price") or 0),
                "unit_price": str(r.get("price") or 0),
            }
        )
    return products
