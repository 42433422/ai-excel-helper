from __future__ import annotations

from collections.abc import Mapping


def _column_name_set(column_names: set[str] | Mapping[str, object]) -> set[str]:
    if isinstance(column_names, Mapping):
        return set(column_names.keys())
    return set(column_names)


def scoped_mod_id() -> str | None:
    try:
        from app.request_active_mod_ctx import get_request_active_mod_id
    except ModuleNotFoundError:
        return None
    v = get_request_active_mod_id().strip()
    return v or None


def append_mod_scope_where(
    where_parts: list[str],
    bind: dict[str, object],
    column_names: set[str] | Mapping[str, object],
) -> None:
    """若表含 xcagi_mod_id 且当前请求带有 X-XCAGI-Active-Mod-Id，则追加按包过滤条件。"""
    cols = _column_name_set(column_names)
    if "xcagi_mod_id" not in cols:
        return
    mid = scoped_mod_id()
    if not mid:
        return
    where_parts.append("xcagi_mod_id = :xmid")
    bind["xmid"] = mid


def products_update_or_delete_mod_and(pcols: set[str], params: dict[str, object]) -> str:
    """UPDATE/DELETE products（及同类按包隔离表）时追加 AND 片段；与 append_mod_scope_where 共用 :xmid。"""
    if "xcagi_mod_id" not in pcols:
        return ""
    mid = scoped_mod_id()
    if not mid:
        return ""
    params["xmid"] = mid
    return " AND xcagi_mod_id = :xmid"
