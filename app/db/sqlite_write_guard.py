"""桌面 SQLite 写路径单飞锁，缓解 database is locked。"""

from __future__ import annotations

import threading
from contextlib import contextmanager

_write_lock = threading.Lock()


@contextmanager
def sqlite_write_guard():
    """串行化桌面环境下的批量写（Excel 导入等）。"""
    from app.desktop_runtime.paths import is_desktop_mode

    if not is_desktop_mode():
        yield
        return
    with _write_lock:
        yield


__all__ = ["sqlite_write_guard"]
