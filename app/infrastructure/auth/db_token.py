"""DB 只读/写入 token 校验。

Phase 5B 从 ``app.legacy.db_read_auth`` + ``app.legacy.db_write_auth`` 吸收。
"""

from __future__ import annotations

import json
import os

from fastapi import HTTPException, Request


def _normalize_mod_for_env(mod_id: str) -> str:
    return (
        "".join(ch if ch.isalnum() else "_" for ch in str(mod_id or "").strip()).strip("_").upper()
    )


def _get_active_mod_id_from_ctx() -> str:
    try:
        from app.request_active_mod_ctx import get_request_active_mod_id

        return str(get_request_active_mod_id() or "").strip()
    except Exception:
        return ""


def _read_lock_disabled() -> bool:
    v = (os.environ.get("FHD_DISABLE_DB_READ_LOCK") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _read_token_map_from_env() -> dict[str, str]:
    raw = (
        os.environ.get("FHD_DB_READ_TOKEN_BY_MODS")
        or os.environ.get("FHD_DB_READ_TOKENS_BY_MOD")
        or ""
    ).strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in obj.items():
        key = str(k or "").strip()
        val = str(v or "").strip()
        if key and val:
            out[key] = val
    return out


def _write_token_map_from_env() -> dict[str, str]:
    raw = (
        os.environ.get("FHD_DB_WRITE_TOKEN_BY_MODS")
        or os.environ.get("FHD_DB_WRITE_TOKENS_BY_MOD")
        or ""
    ).strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in obj.items():
        key = str(k or "").strip()
        val = str(v or "").strip()
        if key and val:
            out[key] = val
    return out


def configured_db_read_token(active_mod_id: str | None = None) -> str | None:
    mid = str(active_mod_id or "").strip() or _get_active_mod_id_from_ctx()
    if mid:
        env_map = _read_token_map_from_env()
        mapped = str(env_map.get(mid) or "").strip()
        if mapped:
            return mapped
        env_key = f"FHD_DB_READ_TOKEN_{_normalize_mod_for_env(mid)}"
        env_specific = str(os.environ.get(env_key) or "").strip()
        if env_specific:
            return env_specific
    t = (os.environ.get("FHD_DB_READ_TOKEN") or "").strip()
    return t or None


def effective_db_read_token() -> str | None:
    """读保护生效时返回须匹配的令牌；未配置读锁时返回 None。

    一级读锁为**显式开启**：仅当配置了 ``FHD_DB_READ_TOKEN``（或按 Mod 映射等）
    时才校验 ``X-FHD-Db-Read-Token``。不设环境变量即不弹窗、不要求头。
    若已配置令牌但希望临时关闭校验，可设 ``FHD_DISABLE_DB_READ_LOCK=1``。
    """
    if _read_lock_disabled():
        return None
    return configured_db_read_token()


def verify_db_read_token_header(request: Request) -> None:
    expected = effective_db_read_token()
    if not expected:
        return
    got = (request.headers.get("X-FHD-Db-Read-Token") or "").strip()
    if got != expected:
        raise HTTPException(status_code=403, detail="只读令牌无效或缺失")


def configured_db_write_token(active_mod_id: str | None = None) -> str | None:
    mid = str(active_mod_id or "").strip() or _get_active_mod_id_from_ctx()
    if mid:
        env_map = _write_token_map_from_env()
        mapped = str(env_map.get(mid) or "").strip()
        if mapped:
            return mapped
        env_key = f"FHD_DB_WRITE_TOKEN_{_normalize_mod_for_env(mid)}"
        env_specific = str(os.environ.get(env_key) or "").strip()
        if env_specific:
            return env_specific
    token = (os.environ.get("FHD_DB_WRITE_TOKEN") or "").strip()
    return token or None


def verify_db_write_token_header(request: Request) -> None:
    expected = configured_db_write_token()
    if not expected:
        return
    got = (request.headers.get("X-FHD-Db-Write-Token") or "").strip()
    if got != expected:
        raise HTTPException(status_code=403, detail="invalid db write token")


__all__ = [
    "configured_db_read_token",
    "effective_db_read_token",
    "verify_db_read_token_header",
    "configured_db_write_token",
    "verify_db_write_token_header",
]
