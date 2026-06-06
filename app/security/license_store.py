"""
一级密钥与会话的持久化层（独立 SQLite 文件）。

- 使用独立 SQLite，避免在主库 schema 上引入安全相关表
- 进程内单例 ``threading.local`` 持锁；表结构幂等创建
- 一级密钥仅存 SHA-256 摘要，明文只在签发那一瞬间返回给管理员一次

表：
- ``lan_license_keys``    一级密钥（哈希、备注、状态、签发/吊销时间、签发人）
- ``lan_license_sessions`` 活跃 / 历史会话（jti、kid、ip、ua、签发/到期/吊销时间）
- ``lan_audit_log``       授权相关审计（动作、操作者、IP、详情）
"""

from __future__ import annotations

import contextlib
import logging
import secrets
import sqlite3
import threading
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass

from app.security.lan_config import get_lan_config
from app.security.license_token import hash_secret

logger = logging.getLogger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS lan_license_keys (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash      TEXT NOT NULL UNIQUE,
    label         TEXT NOT NULL DEFAULT '',
    created_at    INTEGER NOT NULL,
    created_by    TEXT NOT NULL DEFAULT '',
    expires_at    INTEGER,
    revoked_at    INTEGER,
    last_used_at  INTEGER,
    use_count     INTEGER NOT NULL DEFAULT 0,
    is_admin      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_lan_keys_hash ON lan_license_keys(key_hash);

CREATE TABLE IF NOT EXISTS lan_license_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    jti           TEXT NOT NULL UNIQUE,
    key_id        INTEGER,
    kid           TEXT NOT NULL DEFAULT '',
    ip            TEXT NOT NULL DEFAULT '',
    user_agent    TEXT NOT NULL DEFAULT '',
    issued_at     INTEGER NOT NULL,
    expires_at    INTEGER NOT NULL,
    revoked_at    INTEGER,
    last_seen_at  INTEGER
);

CREATE INDEX IF NOT EXISTS ix_lan_sessions_jti ON lan_license_sessions(jti);
CREATE INDEX IF NOT EXISTS ix_lan_sessions_key ON lan_license_sessions(key_id);

CREATE TABLE IF NOT EXISTS lan_audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,
    actor       TEXT NOT NULL DEFAULT '',
    action      TEXT NOT NULL,
    target      TEXT NOT NULL DEFAULT '',
    ip          TEXT NOT NULL DEFAULT '',
    detail      TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_lan_audit_ts ON lan_audit_log(ts);

CREATE TABLE IF NOT EXISTS lan_access_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ip            TEXT NOT NULL,
    device_label  TEXT NOT NULL DEFAULT '',
    note          TEXT NOT NULL DEFAULT '',
    user_agent    TEXT NOT NULL DEFAULT '',
    requested_at  INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    reviewed_at   INTEGER,
    reviewed_by   TEXT NOT NULL DEFAULT '',
    review_note   TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_lan_access_requests_ip ON lan_access_requests(ip);
CREATE INDEX IF NOT EXISTS ix_lan_access_requests_status ON lan_access_requests(status);

CREATE TABLE IF NOT EXISTS lan_allowed_clients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ip            TEXT NOT NULL UNIQUE,
    label         TEXT NOT NULL DEFAULT '',
    note          TEXT NOT NULL DEFAULT '',
    approved_at   INTEGER NOT NULL,
    approved_by   TEXT NOT NULL DEFAULT '',
    request_id    INTEGER,
    revoked_at    INTEGER,
    last_seen_at  INTEGER
);

CREATE INDEX IF NOT EXISTS ix_lan_allowed_clients_ip ON lan_allowed_clients(ip);
CREATE INDEX IF NOT EXISTS ix_lan_allowed_clients_revoked ON lan_allowed_clients(revoked_at);
"""


@dataclass(frozen=True)
class LicenseKey:
    id: int
    label: str
    created_at: int
    created_by: str
    expires_at: int | None
    revoked_at: int | None
    last_used_at: int | None
    use_count: int
    is_admin: bool


@dataclass(frozen=True)
class LicenseSession:
    id: int
    jti: str
    key_id: int | None
    kid: str
    ip: str
    user_agent: str
    issued_at: int
    expires_at: int
    revoked_at: int | None
    last_seen_at: int | None


@dataclass(frozen=True)
class AuditEntry:
    id: int
    ts: int
    actor: str
    action: str
    target: str
    ip: str
    detail: str


@dataclass(frozen=True)
class AccessRequest:
    id: int
    ip: str
    device_label: str
    note: str
    user_agent: str
    requested_at: int
    status: str
    reviewed_at: int | None
    reviewed_by: str
    review_note: str


@dataclass(frozen=True)
class AllowedClient:
    id: int
    ip: str
    label: str
    note: str
    approved_at: int
    approved_by: str
    request_id: int | None
    revoked_at: int | None
    last_seen_at: int | None


_lock = threading.Lock()
_initialized = False


def _now() -> int:
    return int(time.time())


@contextlib.contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    cfg = get_lan_config()
    path = str(cfg.license_db_path)
    conn = sqlite3.connect(path, timeout=10.0, isolation_level=None, check_same_thread=False)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    finally:
        conn.close()


def ensure_schema() -> None:
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        with _connect() as conn:
            conn.executescript(_SCHEMA)
        _initialized = True
        logger.info("LAN license store schema ensured at %s", get_lan_config().license_db_path)


def _row_to_key(row: sqlite3.Row) -> LicenseKey:
    return LicenseKey(
        id=int(row["id"]),
        label=row["label"] or "",
        created_at=int(row["created_at"]),
        created_by=row["created_by"] or "",
        expires_at=int(row["expires_at"]) if row["expires_at"] is not None else None,
        revoked_at=int(row["revoked_at"]) if row["revoked_at"] is not None else None,
        last_used_at=int(row["last_used_at"]) if row["last_used_at"] is not None else None,
        use_count=int(row["use_count"] or 0),
        is_admin=bool(int(row["is_admin"] or 0)),
    )


def _row_to_session(row: sqlite3.Row) -> LicenseSession:
    return LicenseSession(
        id=int(row["id"]),
        jti=row["jti"],
        key_id=int(row["key_id"]) if row["key_id"] is not None else None,
        kid=row["kid"] or "",
        ip=row["ip"] or "",
        user_agent=row["user_agent"] or "",
        issued_at=int(row["issued_at"]),
        expires_at=int(row["expires_at"]),
        revoked_at=int(row["revoked_at"]) if row["revoked_at"] is not None else None,
        last_seen_at=int(row["last_seen_at"]) if row["last_seen_at"] is not None else None,
    )


def _row_to_audit(row: sqlite3.Row) -> AuditEntry:
    return AuditEntry(
        id=int(row["id"]),
        ts=int(row["ts"]),
        actor=row["actor"] or "",
        action=row["action"] or "",
        target=row["target"] or "",
        ip=row["ip"] or "",
        detail=row["detail"] or "",
    )


def _row_to_access_request(row: sqlite3.Row) -> AccessRequest:
    return AccessRequest(
        id=int(row["id"]),
        ip=row["ip"] or "",
        device_label=row["device_label"] or "",
        note=row["note"] or "",
        user_agent=row["user_agent"] or "",
        requested_at=int(row["requested_at"]),
        status=row["status"] or "pending",
        reviewed_at=int(row["reviewed_at"]) if row["reviewed_at"] is not None else None,
        reviewed_by=row["reviewed_by"] or "",
        review_note=row["review_note"] or "",
    )


def _row_to_allowed_client(row: sqlite3.Row) -> AllowedClient:
    return AllowedClient(
        id=int(row["id"]),
        ip=row["ip"] or "",
        label=row["label"] or "",
        note=row["note"] or "",
        approved_at=int(row["approved_at"]),
        approved_by=row["approved_by"] or "",
        request_id=int(row["request_id"]) if row["request_id"] is not None else None,
        revoked_at=int(row["revoked_at"]) if row["revoked_at"] is not None else None,
        last_seen_at=int(row["last_seen_at"]) if row["last_seen_at"] is not None else None,
    )


# ---------------------------------------------------------------------------
# 一级密钥
# ---------------------------------------------------------------------------


def issue_key(
    *,
    label: str = "",
    created_by: str = "",
    expires_at: int | None = None,
    is_admin: bool = False,
    plaintext: str | None = None,
) -> tuple[str, LicenseKey]:
    """
    生成（或登记给定明文）一把一级密钥；返回明文与对应记录。
    明文之后无法再被读出。
    """
    ensure_schema()
    secret_text = (plaintext or secrets.token_urlsafe(24)).strip()
    if not secret_text:
        raise ValueError("plaintext key must not be empty")
    digest = hash_secret(secret_text)
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO lan_license_keys"
            " (key_hash, label, created_at, created_by, expires_at, is_admin)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (digest, label.strip(), now, created_by.strip(), expires_at, 1 if is_admin else 0),
        )
        new_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM lan_license_keys WHERE id=?", (new_id,)).fetchone()
    return secret_text, _row_to_key(row)


def list_keys(include_revoked: bool = True) -> list[LicenseKey]:
    ensure_schema()
    sql = "SELECT * FROM lan_license_keys"
    if not include_revoked:
        sql += " WHERE revoked_at IS NULL"
    sql += " ORDER BY id DESC"
    with _connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_key(r) for r in rows]


def find_key_by_plaintext(plaintext: str) -> LicenseKey | None:
    ensure_schema()
    digest = hash_secret(plaintext)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM lan_license_keys WHERE key_hash=?", (digest,)).fetchone()
    return _row_to_key(row) if row else None


def revoke_key(key_id: int, *, actor: str = "", ip: str = "") -> bool:
    ensure_schema()
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE lan_license_keys SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
            (now, int(key_id)),
        )
        ok = cur.rowcount > 0
        if ok:
            conn.execute(
                "UPDATE lan_license_sessions SET revoked_at=? WHERE key_id=? AND revoked_at IS NULL",
                (now, int(key_id)),
            )
    if ok:
        write_audit(action="key.revoke", target=f"key:{key_id}", actor=actor, ip=ip)
    return ok


def mark_key_used(key_id: int) -> None:
    ensure_schema()
    now = _now()
    with _connect() as conn:
        conn.execute(
            "UPDATE lan_license_keys SET last_used_at=?, use_count=use_count+1 WHERE id=?",
            (now, int(key_id)),
        )


def has_any_active_key() -> bool:
    ensure_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(1) AS n FROM lan_license_keys WHERE revoked_at IS NULL"
        ).fetchone()
    return int(row["n"] or 0) > 0


def has_any_admin_key() -> bool:
    ensure_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(1) AS n FROM lan_license_keys WHERE revoked_at IS NULL AND is_admin=1"
        ).fetchone()
    return int(row["n"] or 0) > 0


# ---------------------------------------------------------------------------
# 会话
# ---------------------------------------------------------------------------


def record_session(
    *,
    jti: str,
    key_id: int | None,
    kid: str,
    ip: str,
    user_agent: str,
    issued_at: int,
    expires_at: int,
) -> LicenseSession:
    ensure_schema()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO lan_license_sessions"
            " (jti, key_id, kid, ip, user_agent, issued_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (jti, key_id, kid or "", ip or "", user_agent or "", int(issued_at), int(expires_at)),
        )
        new_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM lan_license_sessions WHERE id=?", (new_id,)).fetchone()
    return _row_to_session(row)


def get_active_session_by_jti(jti: str) -> LicenseSession | None:
    ensure_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM lan_license_sessions WHERE jti=? AND revoked_at IS NULL",
            (jti,),
        ).fetchone()
    return _row_to_session(row) if row else None


def list_sessions(active_only: bool = True, limit: int = 200) -> list[LicenseSession]:
    ensure_schema()
    sql = "SELECT * FROM lan_license_sessions"
    if active_only:
        sql += " WHERE revoked_at IS NULL AND expires_at > ?"
        params: tuple = (_now(),)
    else:
        params = ()
    sql += " ORDER BY id DESC LIMIT ?"
    params = params + (int(limit),)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_session(r) for r in rows]


def revoke_session(jti: str, *, actor: str = "", ip: str = "") -> bool:
    ensure_schema()
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE lan_license_sessions SET revoked_at=? WHERE jti=? AND revoked_at IS NULL",
            (now, jti),
        )
        ok = cur.rowcount > 0
    if ok:
        write_audit(action="session.revoke", target=f"jti:{jti}", actor=actor, ip=ip)
    return ok


def touch_session(jti: str) -> None:
    ensure_schema()
    now = _now()
    with _connect() as conn:
        conn.execute(
            "UPDATE lan_license_sessions SET last_seen_at=? WHERE jti=? AND revoked_at IS NULL",
            (now, jti),
        )


# ---------------------------------------------------------------------------
# 审计
# ---------------------------------------------------------------------------


def write_audit(
    *,
    action: str,
    target: str = "",
    actor: str = "",
    ip: str = "",
    detail: str = "",
) -> None:
    ensure_schema()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO lan_audit_log (ts, actor, action, target, ip, detail)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (_now(), actor or "", action, target or "", ip or "", detail or ""),
        )


def list_audit(limit: int = 200) -> list[AuditEntry]:
    ensure_schema()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM lan_audit_log ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()
    return [_row_to_audit(r) for r in rows]


# ---------------------------------------------------------------------------
# 动态白名单 / 访问申请
# ---------------------------------------------------------------------------


def is_ip_explicitly_allowed(ip: str) -> bool:
    ensure_schema()
    norm = str(ip or "").strip()
    if not norm:
        return False
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(1) AS n FROM lan_allowed_clients WHERE ip=? AND revoked_at IS NULL",
            (norm,),
        ).fetchone()
    return int(row["n"] or 0) > 0


def touch_allowed_client(ip: str) -> None:
    ensure_schema()
    norm = str(ip or "").strip()
    if not norm:
        return
    with _connect() as conn:
        conn.execute(
            "UPDATE lan_allowed_clients SET last_seen_at=? WHERE ip=? AND revoked_at IS NULL",
            (_now(), norm),
        )


def list_allowed_clients(active_only: bool = True, limit: int = 200) -> list[AllowedClient]:
    ensure_schema()
    sql = "SELECT * FROM lan_allowed_clients"
    params: tuple = ()
    if active_only:
        sql += " WHERE revoked_at IS NULL"
    sql += " ORDER BY approved_at DESC, id DESC LIMIT ?"
    params = params + (int(limit),)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_allowed_client(r) for r in rows]


def revoke_allowed_client(client_id: int, *, actor: str = "", ip: str = "") -> bool:
    ensure_schema()
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE lan_allowed_clients SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
            (now, int(client_id)),
        )
        ok = cur.rowcount > 0
    if ok:
        write_audit(
            action="allowlist.revoke",
            target=f"allow:{client_id}",
            actor=actor,
            ip=ip,
        )
    return ok


def get_latest_access_request_by_ip(ip: str) -> AccessRequest | None:
    ensure_schema()
    norm = str(ip or "").strip()
    if not norm:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM lan_access_requests WHERE ip=? ORDER BY id DESC LIMIT 1",
            (norm,),
        ).fetchone()
    return _row_to_access_request(row) if row else None


def create_access_request(
    *,
    ip: str,
    device_label: str = "",
    note: str = "",
    user_agent: str = "",
) -> AccessRequest:
    ensure_schema()
    norm_ip = str(ip or "").strip()
    if not norm_ip:
        raise ValueError("ip must not be empty")
    label = str(device_label or "").strip()[:200]
    detail = str(note or "").strip()[:500]
    ua = str(user_agent or "").strip()[:512]
    now = _now()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT * FROM lan_access_requests WHERE ip=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (norm_ip,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE lan_access_requests"
                " SET device_label=?, note=?, user_agent=?, requested_at=?"
                " WHERE id=?",
                (label, detail, ua, now, int(existing["id"])),
            )
            row = conn.execute(
                "SELECT * FROM lan_access_requests WHERE id=?",
                (int(existing["id"]),),
            ).fetchone()
            return _row_to_access_request(row)

        cur = conn.execute(
            "INSERT INTO lan_access_requests"
            " (ip, device_label, note, user_agent, requested_at, status)"
            " VALUES (?, ?, ?, ?, ?, 'pending')",
            (norm_ip, label, detail, ua, now),
        )
        row = conn.execute(
            "SELECT * FROM lan_access_requests WHERE id=?",
            (int(cur.lastrowid),),
        ).fetchone()
    return _row_to_access_request(row)


def list_access_requests(
    *,
    status: str | None = None,
    limit: int = 200,
) -> list[AccessRequest]:
    ensure_schema()
    sql = "SELECT * FROM lan_access_requests"
    params: tuple = ()
    norm_status = str(status or "").strip().lower()
    if norm_status and norm_status != "all":
        sql += " WHERE status=?"
        params = (norm_status,)
    sql += " ORDER BY id DESC LIMIT ?"
    params = params + (int(limit),)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_access_request(r) for r in rows]


def approve_access_request(
    request_id: int,
    *,
    actor: str = "",
    review_note: str = "",
) -> AccessRequest | None:
    ensure_schema()
    now = _now()
    note = str(review_note or "").strip()[:500]
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM lan_access_requests WHERE id=?",
            (int(request_id),),
        ).fetchone()
        if not row:
            return None

        record = _row_to_access_request(row)
        conn.execute(
            "UPDATE lan_access_requests"
            " SET status='approved', reviewed_at=?, reviewed_by=?, review_note=?"
            " WHERE id=?",
            (now, actor or "", note, int(request_id)),
        )
        existing_allow = conn.execute(
            "SELECT id FROM lan_allowed_clients WHERE ip=? LIMIT 1",
            (record.ip,),
        ).fetchone()
        if existing_allow:
            conn.execute(
                "UPDATE lan_allowed_clients"
                " SET label=?, note=?, approved_at=?, approved_by=?, request_id=?, revoked_at=NULL"
                " WHERE id=?",
                (
                    record.device_label,
                    note or record.note,
                    now,
                    actor or "",
                    int(request_id),
                    int(existing_allow["id"]),
                ),
            )
        else:
            conn.execute(
                "INSERT INTO lan_allowed_clients"
                " (ip, label, note, approved_at, approved_by, request_id)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.ip,
                    record.device_label,
                    note or record.note,
                    now,
                    actor or "",
                    int(request_id),
                ),
            )
        updated = conn.execute(
            "SELECT * FROM lan_access_requests WHERE id=?",
            (int(request_id),),
        ).fetchone()
    write_audit(
        action="allowlist.approve",
        target=f"request:{request_id}",
        actor=actor,
        ip=record.ip,
        detail=note or record.device_label,
    )
    return _row_to_access_request(updated) if updated else None


def reject_access_request(
    request_id: int,
    *,
    actor: str = "",
    review_note: str = "",
) -> AccessRequest | None:
    ensure_schema()
    now = _now()
    note = str(review_note or "").strip()[:500]
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM lan_access_requests WHERE id=?",
            (int(request_id),),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE lan_access_requests"
            " SET status='rejected', reviewed_at=?, reviewed_by=?, review_note=?"
            " WHERE id=?",
            (now, actor or "", note, int(request_id)),
        )
        updated = conn.execute(
            "SELECT * FROM lan_access_requests WHERE id=?",
            (int(request_id),),
        ).fetchone()
    record = _row_to_access_request(updated) if updated else None
    if record:
        write_audit(
            action="allowlist.reject",
            target=f"request:{request_id}",
            actor=actor,
            ip=record.ip,
            detail=note or record.device_label,
        )
    return record


def to_dict_key(k: LicenseKey) -> dict:
    return {**asdict(k)}


def to_dict_session(s: LicenseSession) -> dict:
    return {**asdict(s)}


def to_dict_audit(a: AuditEntry) -> dict:
    return {**asdict(a)}


def to_dict_access_request(r: AccessRequest) -> dict:
    return {**asdict(r)}


def to_dict_allowed_client(c: AllowedClient) -> dict:
    return {**asdict(c)}
