"""
多扩展共库时的行级归属：表含 ``xcagi_mod_id`` 且请求带 ``X-XCAGI-Active-Mod-Id`` 时，
产品 / 购买单位 / 客户列表与写操作只作用于当前扩展 id 对应的行。

物理分库仍见 ``mod_database_gate`` 文档；本模块解决「同一 DATABASE_URL、多 manifest」下的数据串台。

迁移：``scripts/pg_init_xcagi_core.sql`` 中的 ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS xcagi_mod_id``；
历史行可执行 ``UPDATE ... SET xcagi_mod_id = '你的包id' WHERE xcagi_mod_id IS NULL`` 分批归属。
"""

from __future__ import annotations

from backend.request_active_mod_ctx import get_request_active_mod_id

COL = "xcagi_mod_id"
BIND = "xcagi_active_mod_scope_bind"


def scoped_mod_id() -> str | None:
    raw = get_request_active_mod_id()
    if not raw:
        return None
    s = str(raw).strip()
    return s or None


def append_mod_scope_where(
    where_parts: list[str],
    params: dict[str, object],
    col_names: set[str],
) -> None:
    """在已有 WHERE 子句片段列表上追加 ``xcagi_mod_id = :bind``（列存在且请求头有扩展 id）。"""
    mid = scoped_mod_id()
    if not mid or COL not in col_names:
        return
    where_parts.append(f"{COL} = :{BIND}")
    params[BIND] = mid


def products_update_or_delete_mod_and(col_names: set[str], params: dict[str, object]) -> str:
    """追加到 ``WHERE id = :pid`` 之后；返回 `` AND ...`` 片段（可能为空）。"""
    mid = scoped_mod_id()
    if not mid or COL not in col_names:
        return ""
    params[BIND] = mid
    return f" AND {COL} = :{BIND}"
