"""XCmax 双向同步数据库层（SQLite sidecar）。

该模块管理三张核心表：
  sync_changes  — 变更日志（本地产生或从服务器接收的所有变更）
  sync_outbox   — 待推送到远端服务器的本地变更队列
  sync_inbox    — 从服务器接收、待本地应用的变更队列

游标（cursor）为 sync_changes.id 自增序号，用于断线补拉。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

_DB_FILENAME = "xcmax_sync.db"
_lock = threading.Lock()
_db_path: Path | None = None


def _resolve_db_path() -> Path:
    global _db_path
    if _db_path is not None:
        return _db_path
    try:
        from app.mod_sdk.private_sqlite import resolve_mod_private_sqlite_path

        _db_path = resolve_mod_private_sqlite_path(_DB_FILENAME)
    except Exception:
        base = os.environ.get("DATABASE_PATH") or os.environ.get("XCAGI_DATA_DIR") or os.getcwd()
        _db_path = Path(base) / "mod_dbs" / _DB_FILENAME
        _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    path = _resolve_db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sync_changes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type   TEXT NOT NULL,
            entity_id     TEXT NOT NULL,
            operation     TEXT NOT NULL CHECK(operation IN ('insert','update','delete','sync')),
            payload_json  TEXT NOT NULL DEFAULT '{}',
            version       INTEGER NOT NULL DEFAULT 1,
            actor         TEXT NOT NULL DEFAULT '',
            origin_node   TEXT NOT NULL DEFAULT 'local',
            conflict_flag INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS ix_sync_changes_entity
            ON sync_changes (entity_type, entity_id);

        CREATE INDEX IF NOT EXISTS ix_sync_changes_cursor
            ON sync_changes (id);

        CREATE TABLE IF NOT EXISTS sync_outbox (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            change_id     INTEGER NOT NULL REFERENCES sync_changes(id),
            entity_type   TEXT NOT NULL,
            entity_id     TEXT NOT NULL,
            operation     TEXT NOT NULL,
            payload_json  TEXT NOT NULL DEFAULT '{}',
            remote_host   TEXT NOT NULL DEFAULT '',
            status        TEXT NOT NULL DEFAULT 'pending'
                              CHECK(status IN ('pending','sent','failed','skipped')),
            retry_count   INTEGER NOT NULL DEFAULT 0,
            last_error    TEXT,
            created_at    TEXT NOT NULL,
            sent_at       TEXT
        );

        CREATE INDEX IF NOT EXISTS ix_sync_outbox_status
            ON sync_outbox (status);

        CREATE TABLE IF NOT EXISTS sync_inbox (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_cursor   INTEGER,
            entity_type     TEXT NOT NULL,
            entity_id       TEXT NOT NULL,
            operation       TEXT NOT NULL,
            payload_json    TEXT NOT NULL DEFAULT '{}',
            origin_node     TEXT NOT NULL DEFAULT 'remote',
            status          TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending','applied','conflict','skipped')),
            conflict_note   TEXT,
            received_at     TEXT NOT NULL,
            applied_at      TEXT
        );

        CREATE INDEX IF NOT EXISTS ix_sync_inbox_status
            ON sync_inbox (status);

        CREATE TABLE IF NOT EXISTS sync_meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """
    )
    conn.commit()


class SyncDb:
    """XCmax 同步数据库访问对象。每次操作新建连接（SQLite NullPool 风格）。"""

    def __init__(self) -> None:
        with _get_conn() as conn:
            _ensure_schema(conn)

    # ------------------------------------------------------------------
    # 变更写入
    # ------------------------------------------------------------------

    def append_change(
        self,
        entity_type: str,
        entity_id: str,
        operation: str,
        payload: dict[str, Any],
        *,
        version: int = 1,
        actor: str = "system",
        origin_node: str = "local",
        enqueue_outbox: bool = True,
    ) -> int:
        """记录变更并可选写入 outbox；返回新变更的 cursor id。"""
        now = datetime.now().isoformat(timespec="seconds")
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        with _lock, _get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO sync_changes
                    (entity_type, entity_id, operation, payload_json, version, actor, origin_node, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (entity_type, entity_id, operation, payload_json, version, actor, origin_node, now),
            )
            change_id = cur.lastrowid
            if enqueue_outbox and origin_node == "local":
                conn.execute(
                    """
                    INSERT INTO sync_outbox
                        (change_id, entity_type, entity_id, operation, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (change_id, entity_type, entity_id, operation, payload_json, now),
                )
            conn.commit()
        return change_id  # type: ignore[return-value]

    def enqueue_inbox(
        self,
        items: list[dict[str, Any]],
        remote_cursor: int | None = None,
    ) -> int:
        """将远端变更写入 inbox，返回写入行数。"""
        now = datetime.now().isoformat(timespec="seconds")
        rows = []
        for item in items:
            rows.append(
                (
                    remote_cursor,
                    str(item.get("entity_type") or ""),
                    str(item.get("entity_id") or ""),
                    str(item.get("operation") or "sync"),
                    json.dumps(item.get("payload") or {}, ensure_ascii=False, default=str),
                    str(item.get("origin_node") or "remote"),
                    now,
                )
            )
        if not rows:
            return 0
        with _lock, _get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO sync_inbox
                    (remote_cursor, entity_type, entity_id, operation, payload_json, origin_node, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        with _get_conn() as conn:
            local_cursor_row = conn.execute("SELECT MAX(id) FROM sync_changes").fetchone()
            local_cursor = local_cursor_row[0] if local_cursor_row else None

            remote_cursor_row = conn.execute(
                "SELECT value FROM sync_meta WHERE key='remote_cursor'"
            ).fetchone()
            remote_cursor = int(remote_cursor_row[0]) if remote_cursor_row else None

            last_sync_row = conn.execute(
                "SELECT value FROM sync_meta WHERE key='last_sync_at'"
            ).fetchone()
            last_sync_at = last_sync_row[0] if last_sync_row else None

            outbox_count = conn.execute(
                "SELECT COUNT(*) FROM sync_outbox WHERE status='pending'"
            ).fetchone()[0]
            conflict_count = conn.execute(
                "SELECT COUNT(*) FROM sync_inbox WHERE status='conflict'"
            ).fetchone()[0]

        healthy = outbox_count == 0 and conflict_count == 0
        return {
            "healthy": healthy,
            "local_cursor": local_cursor,
            "remote_cursor": remote_cursor,
            "outbox_count": outbox_count,
            "conflict_count": conflict_count,
            "last_sync_at": last_sync_at,
        }

    def get_changes(
        self,
        since_cursor: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with _get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, entity_type, entity_id, operation, payload_json,
                       version, actor, origin_node, conflict_flag, created_at
                FROM sync_changes WHERE id > ? ORDER BY id LIMIT ?
                """,
                (since_cursor, limit),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["payload"] = json.loads(d.pop("payload_json") or "{}")
            except Exception:
                d["payload"] = {}
            result.append(d)
        return result

    def get_pending_outbox(self, limit: int = 100) -> list[dict[str, Any]]:
        with _get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, change_id, entity_type, entity_id, operation, payload_json, remote_host
                FROM sync_outbox WHERE status='pending' ORDER BY id LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["payload"] = json.loads(d.pop("payload_json") or "{}")
            except Exception:
                d["payload"] = {}
            result.append(d)
        return result

    def mark_outbox_sent(self, outbox_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with _lock, _get_conn() as conn:
            conn.execute(
                "UPDATE sync_outbox SET status='sent', sent_at=? WHERE id=?",
                (now, outbox_id),
            )
            conn.commit()

    def mark_outbox_failed(self, outbox_id: int, error: str, retry: bool = True) -> None:
        with _lock, _get_conn() as conn:
            conn.execute(
                """
                UPDATE sync_outbox
                SET status=?, retry_count=retry_count+1, last_error=?
                WHERE id=?
                """,
                ("pending" if retry else "failed", error, outbox_id),
            )
            conn.commit()

    def update_remote_cursor(self, cursor: int) -> None:
        with _lock, _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('remote_cursor', ?)",
                (str(cursor),),
            )
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('last_sync_at', ?)",
                (now,),
            )
            conn.commit()

    def mark_inbox_applied(self, inbox_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with _lock, _get_conn() as conn:
            conn.execute(
                "UPDATE sync_inbox SET status='applied', applied_at=? WHERE id=?",
                (now, inbox_id),
            )
            conn.commit()

    def mark_inbox_conflict(self, inbox_id: int, note: str) -> None:
        with _lock, _get_conn() as conn:
            conn.execute(
                "UPDATE sync_inbox SET status='conflict', conflict_note=? WHERE id=?",
                (note, inbox_id),
            )
            conn.commit()
