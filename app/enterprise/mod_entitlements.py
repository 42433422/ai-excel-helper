"""企业版 Mod  entitlement：客户 Mod 仅对修茈市场账号绑定的 user_mods 可见。

规则摘要：
- 宿主桥接 Mod（platform_shell 内置包）始终可用。
- 客户 Mod（taiyangniao-pro、sz-qsm-pro 等）仅当出现在当前登录修茈账号的 user_mods 中。
- 本地 FHD ``role=admin`` **不**绕过上述规则（避免「本地管理员看见所有企业 Mod」）。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.mod_sdk.platform_shell import PROTECTED_CLIENT_MOD_IDS
from app.mod_sdk.product_skus import bundled_mod_ids_for_sku, resolve_product_sku

logger = logging.getLogger(__name__)

# 进程内缓存：登录成功后由 legacy_auth 写入；登出清空
_cached_market_user_id: int | None = None
_cached_market_username: str = ""
_cached_entitled_client_mod_ids: set[str] | None = None
_cached_account_kind: str = "enterprise"
_cached_market_is_admin: bool = False


def is_client_mod_id(mod_id: str) -> bool:
    mid = (mod_id or "").strip()
    return mid in PROTECTED_CLIENT_MOD_IDS


def host_mod_ids_for_enterprise() -> frozenset[str]:
    return frozenset(bundled_mod_ids_for_sku("enterprise"))


def enterprise_mod_filter_active() -> bool:
    return resolve_product_sku() == "enterprise"


def get_cached_entitled_client_mod_ids() -> set[str] | None:
    """None 表示非企业版或未登录绑定；set 表示允许加载/展示的客户 Mod id。"""
    if not enterprise_mod_filter_active():
        return None
    return set(_cached_entitled_client_mod_ids or set())


def get_cached_market_identity() -> tuple[int | None, str]:
    return _cached_market_user_id, _cached_market_username


def clear_session_entitlements() -> None:
    global _cached_market_user_id, _cached_market_username, _cached_entitled_client_mod_ids
    global _cached_account_kind, _cached_market_is_admin
    _cached_market_user_id = None
    _cached_market_username = ""
    _cached_entitled_client_mod_ids = None
    _cached_account_kind = "enterprise"
    _cached_market_is_admin = False


def set_session_entitlements(
    *,
    market_user_id: int | None,
    market_username: str,
    entitled_client_mod_ids: set[str],
    account_kind: str = "enterprise",
    market_is_admin: bool = False,
) -> None:
    global _cached_market_user_id, _cached_market_username, _cached_entitled_client_mod_ids
    global _cached_account_kind, _cached_market_is_admin
    _cached_market_user_id = market_user_id
    _cached_market_username = (market_username or "").strip()
    _cached_entitled_client_mod_ids = set(entitled_client_mod_ids)
    _cached_account_kind = (account_kind or "enterprise").strip() or "enterprise"
    _cached_market_is_admin = bool(market_is_admin)


def is_admin_account_session() -> bool:
    return _cached_account_kind == "admin" and _cached_market_is_admin


def is_mod_visible_for_enterprise(mod_id: str) -> bool:
    """企业版下是否允许暴露/加载该 Mod。"""
    from app.enterprise.account_mod_binding import (
        SUNBIRD_CLIENT_MOD_ID,
        is_sunbird_local_username,
    )

    mid = (mod_id or "").strip()
    if not mid:
        return False
    if not enterprise_mod_filter_active():
        return True
    if not is_client_mod_id(mid):
        return True
    if is_admin_account_session():
        return True
    uname = (_cached_market_username or "").strip()
    if is_sunbird_local_username(uname) and mid == SUNBIRD_CLIENT_MOD_ID:
        return True
    try:
        from app.mod_sdk.client_primary_erp import client_primary_mod_on_disk_visible

        if client_primary_mod_on_disk_visible(mid):
            return True
    except Exception:
        logger.debug("client_primary_mod_on_disk_visible skipped", exc_info=True)
    entitled = get_cached_entitled_client_mod_ids()
    if entitled is None:
        return False
    return mid in entitled


def filter_mod_rows_for_enterprise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not enterprise_mod_filter_active():
        return rows
    return [r for r in rows if is_mod_visible_for_enterprise(str(r.get("id") or ""))]


def filter_mod_id_list_for_enterprise(mod_ids: list[str]) -> list[str]:
    if not enterprise_mod_filter_active():
        return mod_ids
    return [m for m in mod_ids if is_mod_visible_for_enterprise(m)]


def _parse_mod_ids_from_market_payload(payload: Any) -> set[str]:
    ids: set[str] = set()
    if not isinstance(payload, dict):
        return ids
    raw_ids = payload.get("mod_ids")
    if isinstance(raw_ids, list):
        for mid in raw_ids:
            s = str(mid).strip()
            if s and is_client_mod_id(s):
                ids.add(s)
        if ids:
            return ids
    data = payload.get("data")
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and isinstance(data.get("mods"), list):
        rows = data["mods"]
    else:
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mid = str(row.get("id") or "").strip()
        if mid:
            ids.add(mid)
    return ids


async def fetch_entitled_client_mod_ids_from_market(market_token: str) -> set[str]:
    """从修茈市场拉取当前账号绑定的客户 Mod（不走 is_admin 全量列表）。"""
    from app.fastapi_routes.market_account import _proxy_json

    tok = (market_token or "").strip()
    if not tok:
        return set()
    auth = tok if tok.lower().startswith("bearer ") else f"Bearer {tok}"
    payload = await _proxy_json(
        "GET",
        "/api/enterprise/entitled-mod-ids",
        authorization=auth,
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        logger.warning("fetch entitled-mod-ids failed: %s", payload)
        return set()
    if isinstance(payload, dict):
        raw = payload.get("mod_ids") or payload.get("data", {}).get("mod_ids")
        if isinstance(raw, list):
            return {str(x).strip() for x in raw if str(x).strip() and is_client_mod_id(str(x))}
    return _parse_mod_ids_from_market_payload(payload)


async def fetch_entitled_client_mod_ids_for_market_user(
    market_token: str,
    target_market_user_id: int,
) -> set[str]:
    """管理员代管：拉取指定市场用户的 user_mods 客户 Mod。"""
    from app.fastapi_routes.market_account import _proxy_json

    tok = (market_token or "").strip()
    if not tok:
        return set()
    auth = tok if tok.lower().startswith("bearer ") else f"Bearer {tok}"
    payload = await _proxy_json(
        "GET",
        f"/api/admin/users/{int(target_market_user_id)}/mods",
        authorization=auth,
        return_error_payload=True,
    )
    if isinstance(payload, dict) and payload.get("__proxy_error__"):
        logger.warning("fetch admin user mods failed: %s", payload)
        return set()
    return _parse_mod_ids_from_market_payload(payload)


async def refresh_session_entitlements_from_market(
    *,
    market_token: str,
    market_user_id: int | None = None,
    market_username: str = "",
    session_id: str = "",
) -> set[str]:
    account_kind = "enterprise"
    market_is_admin = False
    imp_uid: int | None = None
    sid = (session_id or "").strip()
    if sid:
        try:
            from app.application.session_account_meta import load_session_account_meta

            meta = load_session_account_meta(sid) or {}
            account_kind = str(meta.get("account_kind") or "enterprise")
            market_is_admin = bool(meta.get("market_is_admin"))
            imp = meta.get("impersonating_market_user_id")
            if imp is not None:
                imp_uid = int(imp)
        except Exception:
            pass

    if account_kind == "admin" and market_is_admin and imp_uid is not None:
        client_ids = await fetch_entitled_client_mod_ids_for_market_user(market_token, imp_uid)
    elif account_kind == "admin" and market_is_admin:
        client_ids = set(PROTECTED_CLIENT_MOD_IDS)
    else:
        client_ids = await fetch_entitled_client_mod_ids_from_market(market_token)

    set_session_entitlements(
        market_user_id=market_user_id,
        market_username=market_username,
        entitled_client_mod_ids=client_ids,
        account_kind=account_kind,
        market_is_admin=market_is_admin,
    )
    return client_ids


def persist_entitlements_to_session_row(session_id: str, client_ids: set[str]) -> None:
    """写入 sessions 表，便于重启后仍知 market 身份（客户 Mod 列表仍须重新拉取或缓存 JSON）。"""
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if row is None:
                return
            row.market_user_id = _cached_market_user_id
            row.entitled_mod_ids_json = json.dumps(sorted(client_ids), ensure_ascii=False)
            db.commit()
    except Exception:
        logger.exception("persist_entitlements_to_session_row failed")


def restore_entitlements_from_session_row(session_id: str) -> bool:
    sid = (session_id or "").strip()
    if not sid or not enterprise_mod_filter_active():
        return False
    try:
        from app.db.models.user import Session as UserSession
        from app.db.session import get_db

        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if row is None:
                return False
            mid = getattr(row, "market_user_id", None)
            raw = getattr(row, "entitled_mod_ids_json", None) or "[]"
            ids = {str(x) for x in json.loads(raw) if str(x).strip()}
            account_kind = str(getattr(row, "account_kind", None) or "enterprise")
            market_is_admin = bool(getattr(row, "market_is_admin", False))
            set_session_entitlements(
                market_user_id=int(mid) if mid is not None else None,
                market_username=str(getattr(row, "impersonating_username", None) or ""),
                entitled_client_mod_ids=ids,
                account_kind=account_kind,
                market_is_admin=market_is_admin,
            )
            return True
    except Exception:
        logger.exception("restore_entitlements_from_session_row failed")
        return False


def _session_username_for_entitlements(session_id: str) -> str:
    sid = (session_id or "").strip()
    if not sid:
        return ""
    try:
        from app.application.session_account_meta import load_session_account_meta

        meta = load_session_account_meta(sid) or {}
        imp = str(meta.get("impersonating_username") or "").strip()
        if imp:
            return imp
    except Exception:
        pass
    try:
        from app.services.session_service import SessionService

        info = SessionService().validate_session(sid)
        if info and info.get("username"):
            return str(info["username"]).strip()
    except Exception:
        pass
    return ""


def _augment_entitled_for_username(username: str, current: set[str] | None) -> set[str]:
    from app.enterprise.account_mod_binding import augment_entitled_client_mod_ids_for_username

    return augment_entitled_client_mod_ids_for_username(username, current)


async def sync_entitlements_for_session(session_id: str) -> set[str]:
    """企业版：优先用修茈市场 token 刷新 user_mods 权益；失败则回退 session 行缓存。"""
    if not enterprise_mod_filter_active():
        return set()
    sid = (session_id or "").strip()
    if not sid:
        return set()
    try:
        from app.fastapi_routes.market_account import resolve_valid_market_access_token

        tok = await resolve_valid_market_access_token(sid)
        local_username = _session_username_for_entitlements(sid)
        if tok:
            client_ids = await refresh_session_entitlements_from_market(
                market_token=tok,
                market_username=local_username,
                session_id=sid,
            )
            client_ids = _augment_entitled_for_username(local_username, client_ids)
            set_session_entitlements(
                market_user_id=_cached_market_user_id,
                market_username=local_username or _cached_market_username,
                entitled_client_mod_ids=client_ids,
                account_kind=_cached_account_kind,
                market_is_admin=_cached_market_is_admin,
            )
            persist_entitlements_to_session_row(sid, client_ids)
            await reload_enterprise_mods_after_login()
            return client_ids
        restore_entitlements_from_session_row(sid)
        cached = _augment_entitled_for_username(
            local_username, get_cached_entitled_client_mod_ids() or set()
        )
        if cached:
            set_session_entitlements(
                market_user_id=_cached_market_user_id,
                market_username=local_username or _cached_market_username,
                entitled_client_mod_ids=cached,
                account_kind=_cached_account_kind,
                market_is_admin=_cached_market_is_admin,
            )
        return cached
    except Exception:
        logger.exception("sync_entitlements_for_session failed")
        restore_entitlements_from_session_row(sid)
        local_username = _session_username_for_entitlements(sid)
        cached = _augment_entitled_for_username(
            local_username, get_cached_entitled_client_mod_ids() or set()
        )
        return cached


async def reload_enterprise_mods_after_login() -> None:
    """登录后按 entitlement 重新加载 Mod（避免启动时加载了全部客户 Mod）。"""
    if not enterprise_mod_filter_active():
        return
    try:
        from app.enterprise.account_mod_binding import SUNBIRD_CLIENT_MOD_ID
        from app.fastapi_app import get_fastapi_app
        from app.infrastructure.mods.mod_manager import (
            ensure_mod_api_ready,
            get_mod_manager,
            load_mod_routes,
        )

        mm = get_mod_manager()
        loaded = mm.load_all_mods()
        app = get_fastapi_app()
        load_mod_routes(app, mm)
        if SUNBIRD_CLIENT_MOD_ID in loaded or is_mod_visible_for_enterprise(SUNBIRD_CLIENT_MOD_ID):
            ensure_mod_api_ready(SUNBIRD_CLIENT_MOD_ID)
    except Exception:
        logger.exception("reload_enterprise_mods_after_login failed")
