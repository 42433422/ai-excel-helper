"""
ASGI 中间件：cookie / header token 校验。

- 校验 ``LAN_COOKIE_NAME`` 中的 token：HMAC 签名 + 过期时间 + 会话未吊销
- 校验通过后把 ``jti`` / ``key_id`` / ``is_admin`` 注入 ``scope['state']``，路由层可读
- 命中 bypass 时直接放行（健康检查、登录页本身、激活 API、静态资源）
"""

from __future__ import annotations

import json
import logging
import os

from starlette.types import ASGIApp, Receive, Scope, Send

from app.security.lan_config import (
    LAN_LICENSE_SECRET_MIN_LENGTH,
    get_lan_config,
    lan_guard_path_is_bypassed,
)
from app.security.lan_ip import get_client_ip
from app.security.license_store import (
    ensure_schema,
    get_active_session_by_jti,
    list_keys,
    touch_session,
)
from app.security.license_token import TokenError, parse_token

logger = logging.getLogger(__name__)


def _read_cookie(scope: Scope, name: str) -> str | None:
    headers = scope.get("headers") or []
    for k, v in headers:
        try:
            key = k.decode("latin-1") if isinstance(k, bytes) else str(k)
        except Exception:
            continue
        if key.lower() != "cookie":
            continue
        try:
            raw = v.decode("latin-1") if isinstance(v, bytes) else str(v)
        except Exception:
            continue
        for part in raw.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            ck, _, cv = part.partition("=")
            if ck.strip() == name:
                return cv.strip()
    return None


def _read_header(scope: Scope, name: str) -> str | None:
    target = name.lower().encode("latin-1")
    headers = scope.get("headers") or []
    for k, v in headers:
        if isinstance(k, bytes) and k.lower() == target:
            try:
                return v.decode("latin-1") if isinstance(v, bytes) else str(v)
            except Exception:
                return None
    return None


async def _send_json(
    send: Send, status: int, body: dict, extra_headers: list | None = None
) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(payload)).encode("ascii")),
        (b"x-lan-guard", b"license-required"),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": payload, "more_body": False})


class LanLicenseGuard:
    """校验 LAN 许可 token；未通过返回 401，由前端引导到激活页。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        cfg = get_lan_config()
        if not cfg.enabled:
            await self.app(scope, receive, send)
            return

        method = (scope.get("method") or "GET").upper()
        path = scope.get("path") or "/"
        if method == "OPTIONS" or lan_guard_path_is_bypassed(path, cfg):
            await self.app(scope, receive, send)
            return

        if not cfg.is_secret_ready():
            await _send_json(
                send,
                503,
                {
                    "success": False,
                    "error": "license_misconfigured",
                    "message": f"服务端未配置 LAN_LICENSE_SECRET（≥{LAN_LICENSE_SECRET_MIN_LENGTH} 字符）",
                },
            )
            return

        ensure_schema()

        # 管理员主机（admin_host_ips，默认 127.0.0.1 / ::1）自动放行：
        # 后端进程所在的本机天然可信，无需再输入一级密钥；
        # 如果确实需要在本机也走密钥流程，可设环境变量 LAN_ADMIN_HOST_AUTO_BYPASS=0 关闭。
        _auto_bypass_raw = (os.environ.get("LAN_ADMIN_HOST_AUTO_BYPASS") or "1").strip().lower()
        _auto_bypass = _auto_bypass_raw in {"1", "true", "yes", "on"}
        _client_ip_early = get_client_ip(scope, cfg.trusted_proxies)
        if _auto_bypass and _client_ip_early and _client_ip_early in cfg.admin_host_ips:
            scope.setdefault("state", {})
            try:
                scope["state"]["lan_jti"] = "admin_host_bypass"
                scope["state"]["lan_key_id"] = None
                scope["state"]["lan_is_admin"] = True
                scope["state"]["lan_client_ip"] = _client_ip_early
                scope["state"]["lan_session_expires_at"] = 0
                scope["state"]["lan_admin_host_bypass"] = True
            except TypeError:
                pass
            await self.app(scope, receive, send)
            return

        token = _read_cookie(scope, cfg.cookie_name) or _read_header(scope, "X-LAN-Token")
        if not token:
            await _send_json(
                send,
                401,
                {
                    "success": False,
                    "error": "license_required",
                    "message": "未授权：请输入一级密钥激活本机",
                },
            )
            return

        try:
            payload = parse_token(cfg.license_secret, token)
        except TokenError as exc:
            logger.info("LAN token reject: %s", exc)
            await _send_json(
                send,
                401,
                {
                    "success": False,
                    "error": "license_invalid",
                    "message": "授权令牌无效，请重新激活",
                },
            )
            return

        if payload.is_expired():
            await _send_json(
                send,
                401,
                {
                    "success": False,
                    "error": "license_expired",
                    "message": "授权令牌已过期，请重新激活",
                },
            )
            return

        sess = get_active_session_by_jti(payload.jti)
        if not sess:
            await _send_json(
                send,
                401,
                {
                    "success": False,
                    "error": "license_revoked",
                    "message": "会话已被吊销或不存在",
                },
            )
            return

        is_admin_session = False
        if sess.key_id is not None:
            for k in list_keys(include_revoked=False):
                if k.id == sess.key_id:
                    is_admin_session = bool(k.is_admin)
                    break

        client_ip = get_client_ip(scope, cfg.trusted_proxies)
        scope.setdefault("state", {})
        try:
            scope["state"]["lan_jti"] = payload.jti
            scope["state"]["lan_key_id"] = sess.key_id
            scope["state"]["lan_is_admin"] = is_admin_session
            scope["state"]["lan_client_ip"] = client_ip
            scope["state"]["lan_session_expires_at"] = payload.exp
        except TypeError:
            pass

        try:
            touch_session(payload.jti)
        except Exception:
            logger.debug("touch_session failed for jti=%s", payload.jti, exc_info=True)

        await self.app(scope, receive, send)
