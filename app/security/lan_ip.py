"""
客户端真实 IP 提取。

X-Forwarded-For 默认 **不信任**。只有当上游代理 IP 命中
``LAN_TRUSTED_PROXIES`` 时，才会从 XFF 链中取最左可信跳作为客户端 IP。
这样能避免把伪造头当成"内网请求"绕过 CIDR 白名单。
"""

from __future__ import annotations

from collections.abc import Iterable
from ipaddress import ip_address, ip_network

from starlette.types import Scope


def _peer_ip(scope: Scope) -> str | None:
    client = scope.get("client") if isinstance(scope, dict) else None
    if not client:
        return None
    if isinstance(client, (tuple, list)) and len(client) >= 1:
        return str(client[0])
    return None


def _normalize(ip: str | None) -> str | None:
    if not ip:
        return None
    ip = ip.strip()
    if ip.startswith("[") and ip.endswith("]"):
        ip = ip[1:-1]
    if ":" in ip and ip.count(":") == 1 and not ip.startswith("::"):
        ip = ip.split(":", 1)[0]
    try:
        return str(ip_address(ip))
    except ValueError:
        return None


def _proxy_matches(peer: str, trusted: Iterable[str]) -> bool:
    if not peer:
        return False
    try:
        peer_obj = ip_address(peer)
    except ValueError:
        return False
    for entry in trusted:
        entry = (entry or "").strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if peer_obj in ip_network(entry, strict=False):
                    return True
            elif peer_obj == ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def _xff_chain(scope: Scope) -> list[str]:
    headers = scope.get("headers") or []
    if not isinstance(headers, list):
        return []
    for k, v in headers:
        try:
            name = k.decode("latin-1") if isinstance(k, bytes) else str(k)
        except Exception:
            continue
        if name.lower() == "x-forwarded-for":
            try:
                raw = v.decode("latin-1") if isinstance(v, bytes) else str(v)
            except Exception:
                return []
            return [seg.strip() for seg in raw.split(",") if seg.strip()]
    return []


def _real_ip_header(scope: Scope) -> str | None:
    headers = scope.get("headers") or []
    for k, v in headers:
        try:
            name = k.decode("latin-1") if isinstance(k, bytes) else str(k)
        except Exception:
            continue
        if name.lower() == "x-real-ip":
            try:
                return v.decode("latin-1") if isinstance(v, bytes) else str(v)
            except Exception:
                return None
    return None


def get_client_ip(scope: Scope, trusted_proxies: Iterable[str] = ()) -> str | None:
    """
    返回标准化后的客户端 IP；若 socket peer 是已配置的可信代理，则继续解析 XFF。

    无可信代理设置时直接采信 ``scope['client']``，杜绝伪造头绕过 CIDR。
    """
    peer = _peer_ip(scope)
    if not peer:
        return None
    peer_norm = _normalize(peer)
    trusted_list = [t for t in trusted_proxies if t]

    if not trusted_list or not _proxy_matches(peer_norm or peer, trusted_list):
        return peer_norm

    xff = _xff_chain(scope)
    if xff:
        for hop in reversed(xff):
            n = _normalize(hop)
            if n and not _proxy_matches(n, trusted_list):
                return n
        return _normalize(xff[0])

    real = _real_ip_header(scope)
    return _normalize(real) or peer_norm
