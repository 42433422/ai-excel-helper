"""xcagi_compat 路由共享工具函数。

从 xcagi_compat.py 抽取的公共常量与辅助函数，供子模块路由复用。
"""

from __future__ import annotations

import re as _re

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


def sql_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def validate_order_clause(order: str) -> str:
    tokens = [t.strip() for t in order.split(",")]
    validated = []
    for tok in tokens:
        m = _re.match(
            r'^"?(\w+)"?\s+(ASC|DESC)(?:\s+NULLS\s+(?:FIRST|LAST))?$', tok, _re.IGNORECASE
        )
        if not m:
            m2 = _re.match(r'^"?(\w+)"?$', tok, _re.IGNORECASE)
            if m2 and m2.group(1).lower() in _ALLOWED_SQL_COLUMNS:
                validated.append(sql_ident(m2.group(1)))
                continue
            raise ValueError(f"invalid ORDER BY token: {tok!r}")
        col_name = m.group(1).lower()
        if col_name not in _ALLOWED_SQL_COLUMNS and col_name != "id":
            raise ValueError(f"ORDER BY column not allowed: {col_name!r}")
        direction = m.group(2).upper()
        suffix = tok[m.end(2) - len(m.group(2)) + len(m.group(2)) :]
        validated.append(f"{sql_ident(m.group(1))} {direction}{suffix}")
    return ", ".join(validated)
