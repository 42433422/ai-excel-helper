"""UTC 时间工具，替代已弃用的 ``datetime.utcnow()``。"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """返回表示当前 UTC 的 naive ``datetime``，用于 ``DateTime`` 无时区列的读写与比较。"""
    return datetime.now(UTC).replace(tzinfo=None)


def utc_now_iso_z(*, timespec: str = "seconds") -> str:
    """当前 UTC 的 ISO 8601 字符串，固定以 ``Z`` 结尾（用于 JSON、日志文件名等）。"""
    s = datetime.now(UTC).isoformat(timespec=timespec)
    return s.replace("+00:00", "Z")
