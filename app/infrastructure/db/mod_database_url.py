"""按当前请求选中的扩展（X-XCAGI-Active-Mod-Id）解析业务库 URL。

优先级：

1. 环境变量 ``XCAGI_MOD_DATABASE_URLS`` JSON：``{"sz-qsm-pro": "postgresql+psycopg://..."}``
2. 环境变量 ``XCAGI_MOD_DATABASE_URL_{NORMALIZED_MOD_ID}``
3. 若设置 ``XCAGI_MOD_ISOLATED_DATABASES=1``：

   - SQLite：在 ``DATABASE_URL`` 文件 stem 后加 ``__{mod_id}``
   - PostgreSQL：库名改为 ``{原库名}__{mod_id_normalized}``

无扩展 id 时使用基库 ``DATABASE_URL``（例如未选扩展或壳层页）。

Phase 5B 从 ``app.legacy.mod_database_url`` 吸收而来。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote, unquote


def _normalize_mod_for_env(mod_id: str) -> str:
    return (
        "".join(ch if ch.isalnum() else "_" for ch in str(mod_id or "").strip()).strip("_").upper()
    )


def _normalize_mod_file_suffix(mod_id: str) -> str:
    return (
        "".join(ch if ch.isalnum() else "_" for ch in str(mod_id or "").strip()).strip("_").lower()
    )


def _mod_db_url_from_env(active_mod_id: str) -> str:
    if not active_mod_id:
        return ""
    raw_json = (os.environ.get("XCAGI_MOD_DATABASE_URLS") or "").strip()
    if raw_json:
        try:
            obj = json.loads(raw_json)
            if isinstance(obj, dict):
                v = str(obj.get(active_mod_id) or "").strip()
                if v:
                    return v
        except json.JSONDecodeError:
            pass
    env_key = f"XCAGI_MOD_DATABASE_URL_{_normalize_mod_for_env(active_mod_id)}"
    return str(os.environ.get(env_key) or "").strip()


def _isolated_flag() -> bool:
    return (os.environ.get("XCAGI_MOD_ISOLATED_DATABASES") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _sqlite_url_with_mod_suffix(base_url: str, active_mod_id: str) -> str:
    if not active_mod_id or not base_url.lower().startswith("sqlite"):
        return base_url
    suffix = _normalize_mod_file_suffix(active_mod_id)
    if not suffix:
        return base_url
    raw = base_url.split("sqlite:///", 1)[-1].split("?", 1)[0]
    raw = unquote(raw)
    if not raw or raw == ":memory:":
        return base_url
    if os.name == "nt" and raw.startswith("/") and len(raw) > 2 and raw[2] == ":":
        raw = raw[1:]
    p = Path(raw)
    mod_file = p.with_name(f"{p.stem}__{suffix}{p.suffix}")
    return f"sqlite:///{quote(mod_file.as_posix(), safe='/:._-')}"


def _postgres_url_with_mod_db(base_url: str, active_mod_id: str) -> str:
    if not active_mod_id:
        return base_url
    suffix = _normalize_mod_file_suffix(active_mod_id)
    if not suffix:
        return base_url
    try:
        from sqlalchemy.engine import make_url

        u = make_url(base_url)
        if u.get_backend_name() != "postgresql":
            return base_url
        base_db = (u.database or "xcagi").strip()
        if base_db.endswith(f"__{suffix}"):
            return base_url
        new_db = f"{base_db}__{suffix}"
        return u.set(database=new_db).render_as_string(hide_password=False)
    except Exception:
        return base_url


def resolve_database_url_for_active_mod(base_url: str) -> str:
    if not (base_url or "").strip():
        return base_url
    try:
        from app.request_active_mod_ctx import get_request_active_mod_id
    except ImportError:
        return base_url
    mid = str(get_request_active_mod_id() or "").strip()
    if not mid:
        return base_url
    mapped = _mod_db_url_from_env(mid)
    if mapped:
        return mapped
    if not _isolated_flag():
        return base_url
    if base_url.strip().lower().startswith("sqlite"):
        return _sqlite_url_with_mod_suffix(base_url, mid)
    return _postgres_url_with_mod_db(base_url, mid)


__all__ = ["resolve_database_url_for_active_mod"]
