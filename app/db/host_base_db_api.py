"""宿主级 API：始终使用基库 ``DATABASE_URL``，不受 ``X-XCAGI-Active-Mod-Id`` 分库影响。"""

from __future__ import annotations

# 前缀匹配（request.url.path）；Mod 业务数据走 ``/api/mod/<id>/...`` 或显式宿主 ERP 路由。
HOST_BASE_DB_API_PREFIXES: tuple[str, ...] = (
    "/api/approval/",
    "/api/market/",
    "/api/service-bridge/",
    "/api/wechat/",
    "/api/auth/",
    "/api/inventory/",
    "/api/runtime/",
    "/api/mods",
    "/api/system/",
)


def should_use_base_database_for_path(path: str) -> bool:
    p = (path or "").split("?")[0] or ""
    if not p.startswith("/api/"):
        return False
    if p.startswith("/api/mod/"):
        return False
    return any(p.startswith(prefix) for prefix in HOST_BASE_DB_API_PREFIXES)
