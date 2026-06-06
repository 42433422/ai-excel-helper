"""
ASGI 中间件：网段白名单。

放在 CORS 后、业务中间件前。命中白名单才放行；否则直接 403。
对预检 OPTIONS、配置的 bypass 路径 / 静态资源前缀放行，避免误伤健康检查
和登录页本身。
"""

from __future__ import annotations

import json
import logging
from ipaddress import ip_address

from starlette.types import ASGIApp, Receive, Scope, Send

from app.security.lan_config import get_lan_config, lan_guard_path_is_bypassed
from app.security.lan_ip import get_client_ip
from app.security.license_store import is_ip_explicitly_allowed, touch_allowed_client

logger = logging.getLogger(__name__)


def _ip_in_cidrs(ip: str, cidrs) -> bool:
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


async def _send_json(send: Send, status: int, body: dict) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(payload)).encode("ascii")),
                (b"x-lan-guard", b"cidr-blocked"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload, "more_body": False})


class LanCidrGuard:
    """ASGI 中间件：在管道最外层做网段过滤。"""

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

        cidrs = cfg.cidr_objects()
        if not cidrs:
            await self.app(scope, receive, send)
            return

        client_ip = get_client_ip(scope, cfg.trusted_proxies)
        if _ip_in_cidrs(client_ip or "", cidrs) or is_ip_explicitly_allowed(client_ip or ""):
            scope.setdefault("state", {})
            try:
                scope["state"]["lan_client_ip"] = client_ip
            except TypeError:
                pass
            try:
                touch_allowed_client(client_ip or "")
            except Exception:
                logger.debug("touch_allowed_client failed for ip=%s", client_ip, exc_info=True)
            await self.app(scope, receive, send)
            return

        logger.warning("LAN CIDR blocked: ip=%s path=%s", client_ip, path)
        await _send_json(
            send,
            403,
            {
                "success": False,
                "error": "lan_blocked",
                "message": "访问被局域网模式拒绝：当前 IP 不在白名单网段内",
                "ip": client_ip,
            },
        )
