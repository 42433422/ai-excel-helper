"""Session 账号类型、企业品牌名、代管态（三档登录 / 管理员全球权）。"""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.db.models.user import Session as UserSession
from app.db.session import get_db

logger = logging.getLogger(__name__)

AccountKind = Literal["personal", "enterprise", "admin"]
VALID_ACCOUNT_KINDS: frozenset[str] = frozenset({"personal", "enterprise", "admin"})


def normalize_account_kind(raw: Any, *, default: str = "enterprise") -> AccountKind:
    v = str(raw or default).strip().lower()
    if v in VALID_ACCOUNT_KINDS:
        return v  # type: ignore[return-value]
    return default  # type: ignore[return-value]


def extract_market_user_blob(market_result: dict[str, Any] | None) -> dict[str, Any]:
    if not market_result or not isinstance(market_result, dict):
        return {}
    raw = market_result.get("raw")
    if not isinstance(raw, dict):
        return {}
    user_blob = raw.get("user")
    if isinstance(user_blob, dict):
        return user_blob
    data = raw.get("data")
    if isinstance(data, dict):
        inner = data.get("user")
        if isinstance(inner, dict):
            return inner
        return data
    return {}


def company_brand_from_user_blob(blob: dict[str, Any] | None) -> str:
    if not blob or not isinstance(blob, dict):
        return ""
    company = str(blob.get("company") or "").strip()
    if company:
        return company
    display = str(blob.get("display_name") or "").strip()
    if display:
        return display
    return str(blob.get("username") or "").strip()


def validate_account_kind_for_market(
    account_kind: AccountKind,
    *,
    is_enterprise: bool,
    is_market_admin: bool,
) -> str | None:
    """返回错误文案；None 表示通过。"""
    if account_kind == "admin":
        if not is_market_admin:
            return "该入口需要平台管理员账号，请使用管理员账号登录或切换登录方式。"
        return None
    if account_kind == "enterprise":
        if is_market_admin:
            return "管理员账号不能从企业账号入口登录，请切换到管理员入口登录。"
        if not is_enterprise:
            return "该入口需要企业版账号。请联系管理员在修茈市场标注为企业用户。"
        return None
    # personal：阶段一与企业相同
    if is_market_admin:
        return "管理员账号请使用管理员入口登录。"
    if not is_enterprise:
        return "该账号未开通企业版。请联系管理员在修茈市场标注为企业用户。"
    return None


def persist_session_account_meta(
    session_id: str,
    *,
    account_kind: AccountKind,
    company_brand: str = "",
    market_user_id: int | None = None,
    market_is_admin: bool = False,
    market_is_enterprise: bool = False,
    impersonating_market_user_id: int | None = None,
    impersonating_username: str = "",
) -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if row is None:
                return
            row.account_kind = account_kind
            row.company_brand = (company_brand or "").strip()[:256]
            if market_user_id is not None:
                row.market_user_id = int(market_user_id)
            row.market_is_admin = bool(market_is_admin)
            row.market_is_enterprise = bool(market_is_enterprise)
            row.impersonating_market_user_id = (
                int(impersonating_market_user_id)
                if impersonating_market_user_id is not None
                else None
            )
            row.impersonating_username = (impersonating_username or "").strip()[:128]
            db.commit()
    except Exception:
        logger.exception("persist_session_account_meta failed")


def load_session_account_meta(session_id: str) -> dict[str, Any] | None:
    sid = (session_id or "").strip()
    if not sid:
        return None
    try:
        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if row is None:
                return None
            return session_row_to_meta_dict(row)
    except Exception:
        logger.exception("load_session_account_meta failed")
        return None


def session_row_to_meta_dict(row: UserSession) -> dict[str, Any]:
    imp_uid = getattr(row, "impersonating_market_user_id", None)
    return {
        "account_kind": str(getattr(row, "account_kind", None) or "enterprise").strip()
        or "enterprise",
        "company_brand": str(getattr(row, "company_brand", None) or "").strip(),
        "market_user_id": getattr(row, "market_user_id", None),
        "market_is_admin": bool(getattr(row, "market_is_admin", False)),
        "market_is_enterprise": bool(getattr(row, "market_is_enterprise", False)),
        "impersonating_market_user_id": int(imp_uid) if imp_uid is not None else None,
        "impersonating_username": str(getattr(row, "impersonating_username", None) or "").strip(),
    }


def clear_impersonation(session_id: str) -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        with get_db() as db:
            row = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if row is None:
                return
            row.impersonating_market_user_id = None
            row.impersonating_username = ""
            db.commit()
    except Exception:
        logger.exception("clear_impersonation failed")


def is_session_market_admin(session_id: str) -> bool:
    meta = load_session_account_meta(session_id)
    if not meta:
        return False
    return meta.get("account_kind") == "admin" and bool(meta.get("market_is_admin"))


def effective_entitlement_market_user_id(session_id: str) -> int | None:
    meta = load_session_account_meta(session_id)
    if not meta:
        return None
    imp = meta.get("impersonating_market_user_id")
    if imp is not None:
        return int(imp)
    mid = meta.get("market_user_id")
    return int(mid) if mid is not None else None


def audit_admin_action(
    request: Any,
    action: str,
    *,
    target_user_id: int | None = None,
    mod_id: str = "",
    detail: str = "",
) -> None:
    try:
        from app.fastapi_routes.legacy_helpers import _session_id_from_request

        sid = _session_id_from_request(request)
        meta = load_session_account_meta(sid) if sid else None
        operator = (meta or {}).get("impersonating_username") or ""
        if not operator and sid:
            info = load_session_account_meta(sid)
            operator = str((info or {}).get("market_user_id") or "")
        logger.info(
            "admin_audit action=%s session=%s target_user=%s mod_id=%s detail=%s",
            action,
            sid,
            target_user_id,
            mod_id,
            detail or operator,
        )
    except Exception:
        logger.exception("audit_admin_action failed")
