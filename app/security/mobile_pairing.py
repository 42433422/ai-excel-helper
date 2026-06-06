"""桌面 QR 配对短期 nonce 存储（进程内 + 可选文件）。"""

from __future__ import annotations

import secrets
import threading
import time
from typing import Any

_lock = threading.Lock()
_nonces: dict[str, dict[str, Any]] = {}


def issue_pairing_nonce(host: str, port: int, ttl_seconds: int = 300) -> dict[str, Any]:
    nonce = secrets.token_urlsafe(16)
    exp = int(time.time()) + ttl_seconds
    payload = {"host": host, "port": port, "nonce": nonce, "exp": exp}
    with _lock:
        _nonces[nonce] = payload
    return payload


def consume_pairing_nonce(nonce: str) -> dict[str, Any] | None:
    with _lock:
        rec = _nonces.pop(nonce, None)
    if not rec:
        return None
    if int(rec.get("exp") or 0) < int(time.time()):
        return None
    return rec
