"""
用户端 LAN 授权路由：

- ``POST /api/lan/activate``    输入一级密钥换取 cookie token
- ``POST /api/lan/logout``      主动注销当前会话
- ``GET  /api/lan/status``      返回当前 IP、网段/动态白名单、普通密钥是否可换票等
- ``GET  /api/lan/host-info``   公开元信息（是否启用、白名单概要、是否管理员主机）

这些路由全部走 bypass 列表，不被 ``LanLicenseGuard`` 拦截。
"""

from __future__ import annotations

import logging
import time
from ipaddress import ip_address

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.security.lan_config import get_lan_config
from app.security.lan_ip import get_client_ip
from app.security.license_store import (
    create_access_request,
    ensure_schema,
    find_key_by_plaintext,
    get_active_session_by_jti,
    get_latest_access_request_by_ip,
    has_any_active_key,
    has_any_admin_key,
    is_ip_explicitly_allowed,
    issue_key,
    list_keys,
    mark_key_used,
    record_session,
    revoke_session,
    to_dict_access_request,
    write_audit,
)
from app.security.license_token import TokenError, issue_token, parse_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lan", tags=["lan"])


def _ip_in_admin_hosts(ip: str | None, admin_hosts: tuple[str, ...]) -> bool:
    if not ip:
        return False
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    for entry in admin_hosts:
        e = (entry or "").strip()
        if not e:
            continue
        try:
            if addr == ip_address(e):
                return True
        except ValueError:
            continue
    return False


def _ip_in_cidrs(ip: str | None, cidrs) -> bool:
    if not ip:
        return False
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    for net in cidrs:
        try:
            if addr in net:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _set_token_cookie(response: Response, token: str, max_age: int) -> None:
    cfg = get_lan_config()
    response.set_cookie(
        key=cfg.cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite=cfg.cookie_samesite,
        domain=cfg.cookie_domain or None,
        path="/",
    )


def _clear_token_cookie(response: Response) -> None:
    cfg = get_lan_config()
    response.delete_cookie(
        key=cfg.cookie_name,
        path="/",
        domain=cfg.cookie_domain or None,
    )


class ActivateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=512)
    label: str | None = None


class ActivateResponse(BaseModel):
    success: bool
    expires_at: int
    is_admin: bool
    kid: str


class StatusResponse(BaseModel):
    success: bool
    enabled: bool
    ip: str | None
    in_whitelist: bool
    in_static_cidr: bool
    in_dynamic_allowlist: bool
    is_admin_host: bool
    authorized: bool
    is_admin: bool
    expires_at: int | None


class HostInfoResponse(BaseModel):
    enabled: bool
    secret_ready: bool
    bootstrap_available: bool
    has_active_key: bool
    has_admin_key: bool
    cidrs: list[str]
    cookie_name: str
    token_ttl_seconds: int
    is_admin_host: bool
    ip: str | None


class AccessRequestPayload(BaseModel):
    device_label: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=500)


@router.get("/host-info", response_model=HostInfoResponse)
async def host_info(request: Request) -> HostInfoResponse:
    cfg = get_lan_config()
    ensure_schema()
    ip = get_client_ip(request.scope, cfg.trusted_proxies)
    return HostInfoResponse(
        enabled=cfg.enabled,
        secret_ready=cfg.is_secret_ready(),
        bootstrap_available=bool(cfg.admin_bootstrap_key) and not has_any_active_key(),
        has_active_key=has_any_active_key(),
        has_admin_key=has_any_admin_key(),
        cidrs=list(cfg.allowed_cidrs),
        cookie_name=cfg.cookie_name,
        token_ttl_seconds=cfg.token_ttl_seconds,
        is_admin_host=_ip_in_admin_hosts(ip, cfg.admin_host_ips),
        ip=ip,
    )


@router.get("/status", response_model=StatusResponse)
async def status(request: Request) -> StatusResponse:
    cfg = get_lan_config()
    ip = get_client_ip(request.scope, cfg.trusted_proxies)
    in_static = _ip_in_cidrs(ip, cfg.cidr_objects())
    in_dynamic = is_ip_explicitly_allowed(ip or "")
    in_white = in_static or in_dynamic
    is_admin_host = _ip_in_admin_hosts(ip, cfg.admin_host_ips)

    authorized = False
    is_admin = False
    expires_at: int | None = None
    token = request.cookies.get(cfg.cookie_name) or request.headers.get("X-LAN-Token")
    if token and cfg.is_secret_ready():
        try:
            payload = parse_token(cfg.license_secret, token)
            if not payload.is_expired():
                sess = get_active_session_by_jti(payload.jti)
                if sess:
                    authorized = True
                    expires_at = payload.exp
                    if sess.key_id is not None:
                        for k in list_keys(include_revoked=False):
                            if k.id == sess.key_id:
                                is_admin = bool(k.is_admin)
                                break
        except TokenError:
            authorized = False

    return StatusResponse(
        success=True,
        enabled=cfg.enabled,
        ip=ip,
        in_whitelist=in_white,
        in_static_cidr=in_static,
        in_dynamic_allowlist=in_dynamic,
        is_admin_host=is_admin_host,
        authorized=authorized,
        is_admin=is_admin,
        expires_at=expires_at,
    )


@router.get("/access-requests/mine")
async def my_access_request(request: Request) -> dict:
    cfg = get_lan_config()
    ip = get_client_ip(request.scope, cfg.trusted_proxies)
    in_static = _ip_in_cidrs(ip, cfg.cidr_objects())
    in_dynamic = is_ip_explicitly_allowed(ip or "")
    in_white = in_static or in_dynamic
    record = get_latest_access_request_by_ip(ip or "")
    return {
        "success": True,
        "enabled": cfg.enabled,
        "ip": ip,
        "in_whitelist": in_white,
        "in_static_cidr": in_static,
        "in_dynamic_allowlist": in_dynamic,
        "request": to_dict_access_request(record) if record else None,
    }


@router.post("/access-requests")
async def request_access(
    payload: AccessRequestPayload,
    request: Request,
) -> dict:
    cfg = get_lan_config()
    if not cfg.enabled:
        raise HTTPException(status_code=400, detail="lan_mode_disabled")

    ip = get_client_ip(request.scope, cfg.trusted_proxies) or ""
    if is_ip_explicitly_allowed(ip):
        latest = get_latest_access_request_by_ip(ip)
        return {
            "success": True,
            "already_allowed": True,
            "ip": ip,
            "request": to_dict_access_request(latest) if latest else None,
        }

    record = create_access_request(
        ip=ip,
        device_label=payload.device_label,
        note=payload.note,
        user_agent=request.headers.get("user-agent", "")[:512],
    )
    write_audit(
        action="allowlist.request",
        target=f"request:{record.id}",
        actor="anonymous",
        ip=ip,
        detail=f"label={payload.device_label!r}",
    )
    return {"success": True, "request": to_dict_access_request(record), "ip": ip}


@router.post("/activate", response_model=ActivateResponse)
async def activate(req: ActivateRequest, request: Request, response: Response) -> ActivateResponse:
    cfg = get_lan_config()
    if not cfg.enabled:
        raise HTTPException(status_code=400, detail="lan_mode_disabled")
    if not cfg.is_secret_ready():
        raise HTTPException(status_code=503, detail="license_misconfigured")

    ensure_schema()
    ip = get_client_ip(request.scope, cfg.trusted_proxies) or ""
    user_agent = request.headers.get("user-agent", "")[:512]

    # 首道门槛与 LanCidrGuard 一致：须在静态 CIDR 或动态白名单内（避免完全无关网段批量撞密钥）。
    # 非管理员密钥第二道门槛见下方：必须已在动态白名单（管理员批准访问申请）。
    if not (_ip_in_cidrs(ip, cfg.cidr_objects()) or is_ip_explicitly_allowed(ip)):
        write_audit(action="activate.blocked", actor="anonymous", ip=ip, detail="allowlist_block")
        raise HTTPException(status_code=403, detail="lan_blocked")

    plaintext = (req.key or "").strip()
    if not plaintext:
        raise HTTPException(status_code=400, detail="empty_key")

    record = find_key_by_plaintext(plaintext)
    is_admin_session = False
    bootstrap_consumed = False

    if record is not None:
        now = int(time.time())
        if record.revoked_at:
            raise HTTPException(status_code=401, detail="key_revoked")
        if record.expires_at and record.expires_at <= now:
            raise HTTPException(status_code=401, detail="key_expired")
        is_admin_session = record.is_admin
        key_id = record.id
        kid = str(record.id)
    else:
        if (
            cfg.admin_bootstrap_key
            and plaintext == cfg.admin_bootstrap_key
            and not has_any_active_key()
        ):
            label = (req.label or "bootstrap admin").strip() or "bootstrap admin"
            _, new_key = issue_key(
                label=label,
                created_by=f"bootstrap@{ip}",
                is_admin=True,
                plaintext=plaintext,
            )
            is_admin_session = True
            key_id = new_key.id
            kid = str(new_key.id)
            bootstrap_consumed = True
            write_audit(
                action="key.bootstrap",
                target=f"key:{new_key.id}",
                actor=f"bootstrap@{ip}",
                ip=ip,
                detail="bootstrap key promoted to admin",
            )
        else:
            write_audit(action="activate.failed", actor="anonymous", ip=ip, detail="bad_key")
            raise HTTPException(status_code=401, detail="bad_key")

    if not is_admin_session and not is_ip_explicitly_allowed(ip):
        write_audit(
            action="activate.blocked",
            actor="anonymous",
            ip=ip,
            detail="user_key_requires_dynamic_allowlist",
        )
        raise HTTPException(status_code=403, detail="activation_requires_approval")

    if record is not None:
        mark_key_used(record.id)

    token, payload = issue_token(cfg.license_secret, kid=kid, ttl_seconds=cfg.token_ttl_seconds)
    record_session(
        jti=payload.jti,
        key_id=key_id,
        kid=kid,
        ip=ip,
        user_agent=user_agent,
        issued_at=payload.iat,
        expires_at=payload.exp,
    )
    _set_token_cookie(response, token, max_age=cfg.token_ttl_seconds)
    write_audit(
        action="activate.success",
        target=f"key:{key_id}",
        actor=f"key:{key_id}",
        ip=ip,
        detail=("bootstrap" if bootstrap_consumed else "normal"),
    )
    return ActivateResponse(
        success=True,
        expires_at=payload.exp,
        is_admin=is_admin_session,
        kid=kid,
    )


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    cfg = get_lan_config()
    token = request.cookies.get(cfg.cookie_name) or request.headers.get("X-LAN-Token")
    if token and cfg.is_secret_ready():
        try:
            payload = parse_token(cfg.license_secret, token)
            revoke_session(
                payload.jti,
                actor=f"key:{payload.kid}",
                ip=get_client_ip(request.scope, cfg.trusted_proxies) or "",
            )
        except TokenError:
            pass
    _clear_token_cookie(response)
    return {"success": True}
