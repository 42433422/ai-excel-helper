"""
主机管理员控制台 · 局域网安全设置运行时接口。

让管理员在页面上直接启用/关闭 LAN 守护、写入 ``LAN_LICENSE_SECRET``
与 ``LAN_ADMIN_BOOTSTRAP_KEY``，免去"改 .env 再重启"的流程。

- ``GET  /api/lan/admin/settings``   读取当前生效值（secret 字段只返回元数据，不回显明文）
- ``POST /api/lan/admin/settings``   保存覆写，并立刻清缓存；从下一个请求起生效
- ``PUT  /api/lan/admin/settings``   兼容旧前端/代理，语义与 POST 相同

权限策略：
  · 路径在 ``_DEFAULT_BYPASS`` 白名单内，LicenseGuard 放行，避免"刚启用就锁死自己"。
  · LAN **未启用** 时：仅允许来自 ``LAN_ADMIN_HOST_IPS``（默认 127.0.0.1 / ::1）
    的请求，这样外网无法偷偷把 LAN 打开然后塞一把自己的密钥。
  · LAN **已启用** 时：走 ``require_admin`` 双门（管理员主机 或 管理员密钥会话）。
"""

from __future__ import annotations

import logging
import time
from ipaddress import ip_address, ip_network

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from app.security.lan_config import (
    LAN_LICENSE_SECRET_MIN_LENGTH,
    get_lan_config,
    reset_lan_config_cache,
)
from app.security.lan_ip import get_client_ip
from app.security.lan_settings_store import LanSettingsOverride, load_overrides, save_overrides
from app.security.license_store import write_audit

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


def _authorize(request: Request) -> dict:
    """
    返回 actor 信息；未通过直接抛 403。

    - LAN 未启用：仅允许管理员主机 IP（bootstrap 场景）。
    - LAN 已启用：要么管理员主机 IP，要么当前会话是 admin-key。
    """
    cfg = get_lan_config()
    state = request.scope.get("state") or {}
    ip = state.get("lan_client_ip") or get_client_ip(request.scope, cfg.trusted_proxies)
    is_admin_host = _is_admin_host_ip(ip)
    is_admin_key = bool(state.get("lan_is_admin"))

    if cfg.enabled:
        if not (is_admin_host or is_admin_key):
            raise HTTPException(status_code=403, detail="admin_required")
    else:
        # 未启用阶段，license guard 已放行，但仍必须是管理员主机，
        # 否则任意客机都能偷偷打开 LAN 并塞自己的 bootstrap key。
        if not is_admin_host:
            raise HTTPException(status_code=403, detail="admin_host_required")

    return {"ip": ip, "is_admin_host": is_admin_host, "is_admin_key": is_admin_key}


def _mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:2]}{'*' * (len(secret) - 4)}{secret[-2:]}"


class LanSettingsView(BaseModel):
    enabled: bool
    secret_ready: bool
    secret_length: int
    secret_preview: str
    bootstrap_set: bool
    bootstrap_length: int
    bootstrap_preview: str
    allowed_cidrs: list[str] = Field(default_factory=list)
    source: dict = Field(
        default_factory=dict,
        description="每个字段当前是来自 env 还是页面覆写（file）",
    )


class LanSettingsUpdate(BaseModel):
    enabled: bool | None = Field(default=None, description="是否启用 LAN 守护；留空则不改")
    license_secret: str | None = Field(
        default=None,
        min_length=0,
        max_length=256,
        description=f"≥{LAN_LICENSE_SECRET_MIN_LENGTH} 字符的随机串；留空字符串表示清空覆写，回落到 env",
    )
    admin_bootstrap_key: str | None = Field(
        default=None,
        min_length=0,
        max_length=256,
        description="一次性引导密钥；留空字符串表示清空覆写",
    )
    allowed_cidrs: list[str] | None = Field(
        default=None,
        description="CIDR 白名单；传空数组会被拒绝",
    )


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


def _describe_sources() -> dict:
    import os

    overrides = load_overrides()
    return {
        "enabled": "file" if overrides.enabled is not None else "env",
        "license_secret": (
            "file"
            if overrides.license_secret not in (None, "")
            else ("env" if (os.environ.get("LAN_LICENSE_SECRET") or "").strip() else "unset")
        ),
        "admin_bootstrap_key": (
            "file"
            if overrides.admin_bootstrap_key not in (None, "")
            else ("env" if (os.environ.get("LAN_ADMIN_BOOTSTRAP_KEY") or "").strip() else "unset")
        ),
        "allowed_cidrs": (
            "file"
            if overrides.allowed_cidrs is not None
            else ("env" if (os.environ.get("LAN_ALLOWED_CIDRS") or "").strip() else "default")
        ),
    }


@router.get("/settings", response_model=LanSettingsView)
async def get_settings(request: Request) -> LanSettingsView:
    _authorize(request)
    cfg = get_lan_config()
    return LanSettingsView(
        enabled=cfg.enabled,
        secret_ready=cfg.is_secret_ready(),
        secret_length=len(cfg.license_secret or ""),
        secret_preview=_mask(cfg.license_secret or ""),
        bootstrap_set=bool(cfg.admin_bootstrap_key),
        bootstrap_length=len(cfg.admin_bootstrap_key or ""),
        bootstrap_preview=_mask(cfg.admin_bootstrap_key or ""),
        allowed_cidrs=list(cfg.allowed_cidrs),
        source=_describe_sources(),
    )


@router.post("/settings", response_model=LanSettingsView)
@router.put("/settings", response_model=LanSettingsView)
async def update_settings(
    request: Request,
    payload: LanSettingsUpdate = Body(...),
) -> LanSettingsView:
    actor = _authorize(request)

    # 校验：若本次启用 LAN，则必须已有（或正在写入）足够长的 secret。
    incoming_secret: str | None = None
    if payload.license_secret is not None:
        incoming_secret = payload.license_secret.strip()
        if incoming_secret and len(incoming_secret) < LAN_LICENSE_SECRET_MIN_LENGTH:
            raise HTTPException(
                status_code=400,
                detail="license_secret_too_short",
            )
    next_cidrs: list[str] | None = None
    if payload.allowed_cidrs is not None:
        next_cidrs = _normalize_cidrs(payload.allowed_cidrs)

    will_enable = payload.enabled is True
    if will_enable:
        # 判定启用后最终会用哪个 secret
        existing = load_overrides().license_secret
        import os as _os

        env_secret = (_os.environ.get("LAN_LICENSE_SECRET") or "").strip()
        final_secret = (
            incoming_secret
            if incoming_secret is not None
            else (existing if existing is not None else env_secret)
        )
        if not final_secret or len(final_secret) < LAN_LICENSE_SECRET_MIN_LENGTH:
            raise HTTPException(
                status_code=400,
                detail="license_secret_required",
            )

    # 组装覆写（None 表示"不改"；空串表示"清空覆写"）。
    update = LanSettingsOverride(
        enabled=payload.enabled,
        license_secret=incoming_secret,
        admin_bootstrap_key=(
            payload.admin_bootstrap_key.strip() if payload.admin_bootstrap_key is not None else None
        ),
        allowed_cidrs=next_cidrs,
    )

    save_overrides(update, merge=True)
    reset_lan_config_cache()
    cfg = get_lan_config()

    changed = []
    if payload.enabled is not None:
        changed.append(f"enabled={cfg.enabled}")
    if payload.license_secret is not None:
        changed.append(f"license_secret={'set' if cfg.license_secret else 'cleared'}")
    if payload.admin_bootstrap_key is not None:
        changed.append(f"admin_bootstrap_key={'set' if cfg.admin_bootstrap_key else 'cleared'}")
    if payload.allowed_cidrs is not None:
        changed.append(f"allowed_cidrs={len(cfg.allowed_cidrs)}")
    try:
        write_audit(
            action="settings.update",
            target="lan",
            actor=f"admin@{actor.get('ip') or ''}",
            ip=str(actor.get("ip") or ""),
            detail=", ".join(changed) or "noop",
        )
    except Exception:
        logger.debug("audit write failed", exc_info=True)

    _ = time.time()
    return LanSettingsView(
        enabled=cfg.enabled,
        secret_ready=cfg.is_secret_ready(),
        secret_length=len(cfg.license_secret or ""),
        secret_preview=_mask(cfg.license_secret or ""),
        bootstrap_set=bool(cfg.admin_bootstrap_key),
        bootstrap_length=len(cfg.admin_bootstrap_key or ""),
        bootstrap_preview=_mask(cfg.admin_bootstrap_key or ""),
        allowed_cidrs=list(cfg.allowed_cidrs),
        source=_describe_sources(),
    )
