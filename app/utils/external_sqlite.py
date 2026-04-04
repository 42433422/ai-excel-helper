from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator


def connect_sqlite(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


@contextmanager
def sqlite_conn(db_path: str) -> Iterator[sqlite3.Connection]:
    """
    仅用于读取外部 SQLite 数据源（如微信解密库/上传库）。
    主业务数据不得通过该入口访问。
    """
    conn = connect_sqlite(db_path)
    try:
        yield conn
    finally:
        conn.close()
