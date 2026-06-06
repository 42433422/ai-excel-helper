# -*- coding: utf-8 -*-
"""宿主 client_primary_erp_mod_id 与客户 Mod 自管库路由（太阳鸟等）。"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from app.mod_sdk.host_profile import get_client_mod_policies
from app.mod_sdk.platform_shell import PROTECTED_CLIENT_MOD_IDS

logger = logging.getLogger(__name__)


def get_client_primary_erp_mod_id() -> str:
    pol = get_client_mod_policies() or {}
    return str(pol.get("client_primary_erp_mod_id") or "").strip()


def resolve_client_erp_mod_for_request(active_mod_id: str | None = None) -> str:
    """解析本条请求应使用的受保护客户 Mod id（无则空）。"""
    mid = str(active_mod_id or "").strip()
    if mid in PROTECTED_CLIENT_MOD_IDS:
        return mid
    return ""


def _sqlite_customers_list(
    db_path, *, page: int, per_page: int, keyword: str | None
) -> dict[str, Any]:
    if not db_path.exists():
        return {"success": True, "data": [], "total": 0}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cond: list[str] = []
    args: list[Any] = []
    kw = (keyword or "").strip()
    if kw:
        cond.append("(customer_name LIKE ? OR contact_person LIKE ? OR contact_phone LIKE ?)")
        args.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
    where = " AND ".join(cond) if cond else "1=1"
    cur.execute(f"SELECT COUNT(*) FROM customers WHERE {where}", args)
    total = int(cur.fetchone()[0])
    offset = (page - 1) * per_page
    cur.execute(
        "SELECT id, customer_name, contact_person, contact_phone, address, purchase_unit "
        f"FROM customers WHERE {where} ORDER BY id LIMIT ? OFFSET ?",
        [*args, per_page, offset],
    )
    items = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"success": True, "data": items, "total": total}


def try_invoke_client_mod_customers_list(
    *,
    request: Any | None = None,
    page: int = 1,
    per_page: int = 20,
    keyword: str | None = None,
) -> dict[str, Any] | None:
    """
    请求头 / ContextVar 绑定受保护客户 Mod 时，读该 Mod 私有 SQLite，
    避免 xcagi-erp-domain-bridge 误用宿主 PostgreSQL 演示库。
    """
    from app.request_active_mod_ctx import get_request_active_mod_id, parse_active_mod_header

    active = get_request_active_mod_id()
    if not active and request is not None:
        try:
            active = parse_active_mod_header(request.headers)
        except Exception:
            active = ""

    target = resolve_client_erp_mod_for_request(active)
    if not target:
        return None

    try:
        from app.infrastructure.mods.mod_manager import ensure_mod_api_ready, get_mod_manager

        ensure_mod_api_ready(target)
        mm = get_mod_manager()
        mod_path = mm.resolve_mod_directory(target)
        if not mod_path:
            return None
        from app.infrastructure.mods.mod_manager import import_mod_backend_py

        db_mod = import_mod_backend_py(mod_path, target, "database")
        db_path = db_mod.get_database_path()
        out = _sqlite_customers_list(db_path, page=page, per_page=per_page, keyword=keyword)
        out["source"] = f"mod:{target}"
        out["execution_path"] = "client_primary_mod_sqlite"
        return out
    except Exception:
        logger.exception("client mod customers.list failed mod=%s", target)
        return None


def client_primary_mod_on_disk_visible(mod_id: str) -> bool:
    """交付盘：宿主 profile 声明的主 ERP Mod 已落盘时应对列表/加载可见。"""
    mid = str(mod_id or "").strip()
    if mid not in PROTECTED_CLIENT_MOD_IDS:
        return False
    if mid != get_client_primary_erp_mod_id():
        return False
    try:
        from app.desktop_runtime.paths import is_desktop_mode
        from app.infrastructure.mods.mod_manager import get_mod_manager
        from app.mod_sdk.product_skus import resolve_product_sku

        if not is_desktop_mode() and resolve_product_sku() != "enterprise":
            return False
        return bool(get_mod_manager().resolve_mod_directory(mid))
    except Exception:
        logger.debug("client_primary_mod_on_disk_visible check failed", exc_info=True)
        return False


__all__ = [
    "get_client_primary_erp_mod_id",
    "resolve_client_erp_mod_for_request",
    "try_invoke_client_mod_customers_list",
    "client_primary_mod_on_disk_visible",
]
