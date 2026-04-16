"""受控数据库写入：通过环境变量 FHD_DB_WRITE_TOKEN 与请求头 / 聊天体令牌校验。"""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request


def configured_db_write_token() -> str | None:
    t = os.environ.get("FHD_DB_WRITE_TOKEN", "").strip()
    return t or None


def verify_db_write_token_header(request: Request) -> None:
    """
    校验 ``X-FHD-Db-Write-Token`` 请求头与环境变量 ``FHD_DB_WRITE_TOKEN`` 是否一致。
    未配置令牌时拒绝写入（避免误开写接口）。
    """
    expected = configured_db_write_token()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="未配置环境变量 FHD_DB_WRITE_TOKEN，已禁用数据库批量写入。",
        )
    got = (
        request.headers.get("x-fhd-db-write-token")
        or request.headers.get("X-FHD-Db-Write-Token")
        or ""
    ).strip()
    if not secrets.compare_digest(got, expected):
        raise HTTPException(
            status_code=403,
            detail="数据库写入令牌无效或缺失。",
        )


def verify_db_write_token_value(got: str | None) -> bool:
    """供 Planner 工具等非 Request 场景使用；令牌一致返回 True。"""
    expected = configured_db_write_token()
    if not expected or got is None:
        return False
    return secrets.compare_digest((got or "").strip(), expected)
