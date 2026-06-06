"""
管理员 LAN 后台路由：

- ``GET    /api/lan/admin/keys``         列出全部一级密钥（不含明文）
- ``POST   /api/lan/admin/keys``         签发新一级密钥（明文只在响应里返回一次）
- ``DELETE /api/lan/admin/keys/{key_id}``  吊销密钥并连带吊销其活跃会话
- ``GET    /api/lan/admin/sessions``     列出活跃 / 全部会话
- ``DELETE /api/lan/admin/sessions/{jti}`` 踢人
- ``GET    /api/lan/admin/audit``        查看授权审计日志
- ``GET    /api/lan/admin/whoami``       回显当前管理员身份

授权策略（双门）：
  ① 必须已通过 ``LanLicenseGuard``（即有有效会话）
  ② **要么** 当前会话来自 ``LAN_ADMIN_HOST_IPS``（"主机即管理员"）
     **要么** 当前会话使用的密钥是 admin 级
"""

import logging
import time
from ipaddress import ip_address, ip_network

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field

from app.security.lan_config import LAN_LICENSE_SECRET_MIN_LENGTH, get_lan_config
from app.security.lan_ip import get_client_ip
from app.security.license_store import (
    AccessRequest,
    AllowedClient,
    AuditEntry,
    LicenseKey,
    LicenseSession,
    approve_access_request,
    issue_key,
    list_access_requests,
    list_allowed_clients,
    list_audit,
    list_keys,
    list_sessions,
    reject_access_request,
    revoke_allowed_client,
    revoke_key,
    revoke_session,
    to_dict_access_request,
    to_dict_allowed_client,
    to_dict_audit,
    to_dict_key,
    to_dict_session,
    write_audit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lan/admin", tags=["lan-admin"])


def _is_admin_host_ip(ip: str | None) -> bool:
    if not ip:
        return False
    cfg = get_lan_config()
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    for entry in cfg.admin_host_ips:
        e = (entry or "").strip()
        if not e:
            continue
        try:
            if addr == ip_address(e):
                return True
        except ValueError:
            continue
    return False


def require_admin_host(request: Request) -> dict:
    """
    仅要求当前请求来自管理员主机 IP，不检查 LAN 是否开启，也不看密钥。
    用于 settings 的读取和保存。
    """
    cfg = get_lan_config()
    ip = get_client_ip(request.scope, cfg.trusted_proxies)
    if not _is_admin_host_ip(ip):
        raise HTTPException(status_code=403, detail="admin_host_required")
    return {"ip": ip, "is_admin_host": True}


def require_admin(request: Request) -> dict:
    """
    依赖：要求当前请求要么来自管理员主机 IP，要么使用 admin 级一级密钥的会话。
    成功返回 ``{ip, jti, key_id, is_admin_host, is_admin_key}``。
    """
    cfg = get_lan_config()

    state = request.scope.get("state") or {}
    ip = state.get("lan_client_ip") or get_client_ip(request.scope, cfg.trusted_proxies)
    is_admin_host = _is_admin_host_ip(ip)
    is_admin_key = bool(state.get("lan_is_admin"))

    if not (is_admin_host or is_admin_key):
        raise HTTPException(status_code=403, detail="admin_required")

    return {
        "ip": ip,
        "jti": state.get("lan_jti"),
        "key_id": state.get("lan_key_id"),
        "is_admin_host": is_admin_host,
        "is_admin_key": is_admin_key,
    }


class IssueKeyRequest(BaseModel):
    label: str = Field(default="", max_length=200)
    is_admin: bool = False
    expires_at: int | None = Field(default=None, description="Unix 秒；不填表示永不过期")
    plaintext: str | None = Field(
        default=None,
        max_length=512,
        description="可选，传入想要的明文；不传则后端随机生成 24 字节 base64",
    )


class IssueKeyResponse(BaseModel):
    success: bool
    plaintext: str
    key: dict


class AccessRequestReview(BaseModel):
    note: str = Field(default="", max_length=500)


@router.get("/whoami")
async def whoami(actor: dict = Depends(require_admin)) -> dict:
    return {"success": True, **actor}


@router.get("/keys")
async def list_keys_endpoint(
    actor: dict = Depends(require_admin),
    include_revoked: bool = True,
) -> dict:
    keys: list[LicenseKey] = list_keys(include_revoked=include_revoked)
    return {"success": True, "data": [to_dict_key(k) for k in keys]}


@router.post("/keys", response_model=IssueKeyResponse)
async def issue_key_endpoint(
    payload: IssueKeyRequest,
    actor: dict = Depends(require_admin),
) -> IssueKeyResponse:
    if payload.expires_at and payload.expires_at <= int(time.time()):
        raise HTTPException(status_code=400, detail="expires_at_in_past")
    plaintext, record = issue_key(
        label=payload.label,
        created_by=f"admin@{actor.get('ip', '')}",
        expires_at=payload.expires_at,
        is_admin=payload.is_admin,
        plaintext=payload.plaintext,
    )
    write_audit(
        action="key.issue",
        target=f"key:{record.id}",
        actor=f"admin@{actor.get('ip', '')}",
        ip=str(actor.get("ip") or ""),
        detail=f"label={payload.label!r} is_admin={payload.is_admin}",
    )
    return IssueKeyResponse(success=True, plaintext=plaintext, key=to_dict_key(record))


@router.delete("/keys/{key_id}")
async def revoke_key_endpoint(
    key_id: int = Path(..., ge=1),
    actor: dict = Depends(require_admin),
) -> dict:
    ok = revoke_key(key_id, actor=f"admin@{actor.get('ip', '')}", ip=str(actor.get("ip") or ""))
    if not ok:
        raise HTTPException(status_code=404, detail="key_not_found_or_already_revoked")
    return {"success": True}


@router.get("/sessions")
async def list_sessions_endpoint(
    actor: dict = Depends(require_admin),
    active_only: bool = True,
    limit: int = 200,
) -> dict:
    sessions: list[LicenseSession] = list_sessions(active_only=active_only, limit=int(limit))
    return {"success": True, "data": [to_dict_session(s) for s in sessions]}


@router.delete("/sessions/{jti}")
async def kick_session_endpoint(
    jti: str = Path(..., min_length=1, max_length=128),
    actor: dict = Depends(require_admin),
) -> dict:
    ok = revoke_session(jti, actor=f"admin@{actor.get('ip', '')}", ip=str(actor.get("ip") or ""))
    if not ok:
        raise HTTPException(status_code=404, detail="session_not_found_or_revoked")
    return {"success": True}


@router.get("/audit")
async def list_audit_endpoint(
    actor: dict = Depends(require_admin),
    limit: int = 200,
) -> dict:
    entries: list[AuditEntry] = list_audit(limit=int(limit))
    return {"success": True, "data": [to_dict_audit(e) for e in entries]}


@router.get("/access-requests")
async def list_access_requests_endpoint(
    actor: dict = Depends(require_admin),
    status: str = "pending",
    limit: int = 200,
) -> dict:
    entries: list[AccessRequest] = list_access_requests(status=status, limit=int(limit))
    return {"success": True, "data": [to_dict_access_request(e) for e in entries]}


@router.post("/access-requests/{request_id}/approve")
async def approve_access_request_endpoint(
    request_id: int = Path(..., ge=1),
    payload: AccessRequestReview = Body(default=AccessRequestReview()),
    actor: dict = Depends(require_admin),
) -> dict:
    updated = approve_access_request(
        request_id,
        actor=f"admin@{actor.get('ip', '')}",
        review_note=payload.note,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="request_not_found")
    return {"success": True, "data": to_dict_access_request(updated)}


@router.post("/access-requests/{request_id}/reject")
async def reject_access_request_endpoint(
    request_id: int = Path(..., ge=1),
    payload: AccessRequestReview = Body(default=AccessRequestReview()),
    actor: dict = Depends(require_admin),
) -> dict:
    updated = reject_access_request(
        request_id,
        actor=f"admin@{actor.get('ip', '')}",
        review_note=payload.note,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="request_not_found")
    return {"success": True, "data": to_dict_access_request(updated)}


@router.get("/allowlist")
async def list_allowlist_endpoint(
    actor: dict = Depends(require_admin),
    active_only: bool = True,
    limit: int = 200,
) -> dict:
    rows: list[AllowedClient] = list_allowed_clients(active_only=active_only, limit=int(limit))
    return {"success": True, "data": [to_dict_allowed_client(row) for row in rows]}


@router.delete("/allowlist/{client_id}")
async def revoke_allowlist_endpoint(
    client_id: int = Path(..., ge=1),
    actor: dict = Depends(require_admin),
) -> dict:
    ok = revoke_allowed_client(
        client_id,
        actor=f"admin@{actor.get('ip', '')}",
        ip=str(actor.get("ip") or ""),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="allowlist_not_found")
    return {"success": True}


class SettingsUpdate(BaseModel):
    enabled: bool | None = None
    license_secret: str | None = None
    admin_bootstrap_key: str | None = None
    allowed_cidrs: list[str] | None = None


def _rebuild_lan_admin_openapi_models() -> None:
    for _cls in (IssueKeyRequest, IssueKeyResponse, AccessRequestReview, SettingsUpdate):
        _cls.model_rebuild()


_rebuild_lan_admin_openapi_models()


def _normalize_cidrs(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = str(raw or "").strip()
        if not item:
            continue
        try:
            cidr = str(ip_network(item, strict=False))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid_cidr:{item}")
        if cidr in seen:
            continue
        seen.add(cidr)
        normalized.append(cidr)
    if not normalized:
        raise HTTPException(status_code=400, detail="allowed_cidrs_empty")
    return normalized


# ``/api/lan/admin/settings`` 的规范实现位于 ``app/fastapi_routes/lan_settings_routes.py``
# （使用 ``LanSettingsView`` 响应模型）；该路由在 ``register_all_routes`` 中于本
# 模块之后注册，运行时会覆盖下面的实现。这里保留函数体是为了 ``update_settings``
# 的回读依赖（``return await get_settings(actor)``），但从 OpenAPI 文档中隐藏以避免
# Duplicate Operation ID 告警。
@router.get("/settings", include_in_schema=False)
async def get_settings(actor: dict = Depends(require_admin_host)) -> dict:
    import os

    from app.security.lan_settings_store import load_overrides

    cfg = get_lan_config()
    overrides = load_overrides()

    env_enabled = (os.environ.get("LAN_GUARD_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    env_secret = (os.environ.get("LAN_LICENSE_SECRET") or "").strip()
    env_bootstrap = (os.environ.get("LAN_ADMIN_BOOTSTRAP_KEY") or "").strip()
    env_cidrs = (os.environ.get("LAN_ALLOWED_CIDRS") or "").strip()

    def _source(key: str) -> str:
        override_val = getattr(overrides, key, None)
        if override_val is not None:
            return "file"
        if key == "allowed_cidrs":
            if overrides.allowed_cidrs is not None:
                return "file"
            if env_cidrs:
                return "env"
            return "default"
        env_val = {
            "enabled": env_enabled,
            "license_secret": env_secret,
            "admin_bootstrap_key": env_bootstrap,
        }[key]
        if env_val or (key == "enabled" and env_val):
            return "env"
        return "unset"

    return {
        "enabled": cfg.enabled,
        "secret_ready": cfg.is_secret_ready(),
        "secret_length": len(cfg.license_secret) if cfg.license_secret else 0,
        "secret_preview": (
            (cfg.license_secret[:4] + "***" + cfg.license_secret[-4:])
            if cfg.license_secret and len(cfg.license_secret) >= 8
            else ""
        ),
        "bootstrap_set": bool(cfg.admin_bootstrap_key),
        "bootstrap_length": len(cfg.admin_bootstrap_key) if cfg.admin_bootstrap_key else 0,
        "bootstrap_preview": (
            (cfg.admin_bootstrap_key[:4] + "***" + cfg.admin_bootstrap_key[-4:])
            if cfg.admin_bootstrap_key and len(cfg.admin_bootstrap_key) >= 8
            else ""
        ),
        "allowed_cidrs": list(cfg.allowed_cidrs),
        "source": {
            "enabled": _source("enabled"),
            "license_secret": _source("license_secret"),
            "admin_bootstrap_key": _source("admin_bootstrap_key"),
            "allowed_cidrs": _source("allowed_cidrs"),
        },
    }


@router.post("/settings", include_in_schema=False)
@router.put("/settings", include_in_schema=False)
async def update_settings(
    payload: SettingsUpdate, actor: dict = Depends(require_admin_host)
) -> dict:
    from app.security.lan_config import reset_lan_config_cache
    from app.security.lan_settings_store import LanSettingsOverride, save_overrides

    if payload.license_secret is not None:
        if len(payload.license_secret) < LAN_LICENSE_SECRET_MIN_LENGTH:
            raise HTTPException(status_code=400, detail="license_secret_too_short")
    next_cidrs: list[str] | None = None
    if payload.allowed_cidrs is not None:
        next_cidrs = _normalize_cidrs(payload.allowed_cidrs)

    override = LanSettingsOverride(
        enabled=payload.enabled,
        license_secret=payload.license_secret,
        admin_bootstrap_key=payload.admin_bootstrap_key,
        allowed_cidrs=next_cidrs,
    )
    save_overrides(override, merge=True)
    reset_lan_config_cache()

    return await get_settings(actor)
