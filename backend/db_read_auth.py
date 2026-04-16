"""数据库只读访问：默认开启一级锁；显式关闭见 FHD_DISABLE_DB_READ_LOCK。"""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request

_DEFAULT_DEV_READ_TOKEN = "61408693"


def _truthy_env(key: str) -> bool:
    v = os.environ.get(key, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def configured_db_read_token() -> str | None:
    """
    生效的一级读令牌；仅在显式关闭时返回 None。

    优先级：
      1. ``FHD_DISABLE_DB_READ_LOCK=1`` 等 → 关闭只读门禁（兼容测试与旧部署）
      2. ``FHD_DB_READ_TOKEN`` 非空
      3. ``FHD_DB_WRITE_TOKEN`` 非空（与写入令牌共用，便于只配一项）
      4. 内置默认值 ``61408693``（本地与脚本一致；生产请至少配置 WRITE 或 READ）
    """
    if _truthy_env("FHD_DISABLE_DB_READ_LOCK"):
        return None
    t = os.environ.get("FHD_DB_READ_TOKEN", "").strip()
    if t:
        return t
    w = os.environ.get("FHD_DB_WRITE_TOKEN", "").strip()
    if w:
        return w
    return _DEFAULT_DEV_READ_TOKEN


def verify_db_read_token_header(request: Request) -> None:
    """
    当 ``configured_db_read_token()`` 非空时，校验 ``X-FHD-Db-Read-Token`` 与其一致。
    """
    expected = configured_db_read_token()
    if not expected:
        return
    got = (
        request.headers.get("x-fhd-db-read-token")
        or request.headers.get("X-FHD-Db-Read-Token")
        or ""
    ).strip()
    if not secrets.compare_digest(got, expected):
        raise HTTPException(
            status_code=403,
            detail="数据库只读令牌无效或缺失。",
        )
