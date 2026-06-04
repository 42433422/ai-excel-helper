"""
XCAGI 前端兼容 API — 微信联系人相关路由。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

router = APIRouter(tags=["xcagi-compat"])
logger = logging.getLogger(__name__)


class WechatStarredContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = Field(validation_alias=AliasChoices("type", "contactType"))
    nickname: str = Field(validation_alias=AliasChoices("nickname", "备注", "remark"))
    remark: str = Field(default="")
    wxid: str = Field(validation_alias=AliasChoices("wxid", "微信号"))
    starred: bool = Field(default=True)


_STARRED_CONTACTS_DB: dict[str, dict] = {}
_STARRED_NEXT_ID: int = 1


def _migrate_starred_contact_ids() -> None:
    global _STARRED_NEXT_ID
    for _wxid, c in _STARRED_CONTACTS_DB.items():
        if "id" not in c:
            c["id"] = _STARRED_NEXT_ID
            _STARRED_NEXT_ID += 1


def _starred_row_for_frontend(c: dict) -> dict:
    ct = (c.get("type") or "contact").lower()
    return {
        "id": c.get("id"),
        "contact_name": c.get("nickname") or "",
        "remark": c.get("remark") or "",
        "wechat_id": c.get("wxid") or "",
        "contact_type": "group" if ct == "group" else "contact",
        "type": ct,
        "nickname": c.get("nickname"),
        "wxid": c.get("wxid"),
        "starred": bool(c.get("starred", True)),
    }


def _search_hit_for_frontend(c: dict) -> dict:
    row = _starred_row_for_frontend(c)
    row["already_starred"] = True
    dn = (
        (row.get("contact_name") or "").strip()
        or (row.get("remark") or "").strip()
        or (row.get("wechat_id") or "").strip()
    )
    row["display_name"] = dn or "-"
    row["username"] = (row.get("wechat_id") or "").strip()
    row["nick_name"] = (row.get("contact_name") or "").strip()
    return row


@router.get("/wechat_contacts/work_mode_feed")
def wechat_work_mode_feed(per_contact: int = Query(default=1, ge=1, le=100)) -> dict:
    try:
        wechat_decrypt_path = os.environ.get("WECHAT_DECRYPT_PATH", r"e:\FHD\XCAGI\wechat-decrypt")
        if wechat_decrypt_path not in sys.path:
            sys.path.insert(0, wechat_decrypt_path)
        config_file = os.path.join(wechat_decrypt_path, "config.json")
        keys_file = os.path.join(wechat_decrypt_path, "all_keys.json")
        if not os.path.exists(config_file) or not os.path.exists(keys_file):
            return {
                "items": [],
                "per_contact": per_contact,
                "error": "wechat-decrypt not configured",
            }
        with open(config_file) as f:
            cfg = json.load(f)
        with open(keys_file) as f:
            all_keys = json.load(f)
        copy_db_dir = os.path.join(wechat_decrypt_path, "raw_db")
        db_dir = cfg.get("db_dir", "")

        PAGE_SZ = 4096
        RESERVE_SZ = 80
        SALT_SZ = 16
        SQLITE_HDR = b"SQLite format 3\x00"
        KEY_SZ = 32

        def strip_key_metadata(keys):
            if isinstance(keys, dict):
                return keys
            result = []
            for k in keys:
                if isinstance(k, dict):
                    if "enc_key" in k:
                        result.append(k)
                    elif "keys" in k:
                        result.extend(k["keys"])
            return result

        def derive_mac_key(enc_key, salt):
            import hashlib

            mac_salt = bytes(b ^ 0x3A for b in salt)
            return hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=KEY_SZ)

        def decrypt_page(enc_key, page_data, pgno):
            from Crypto.Cipher import AES

            iv = page_data[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + 16]
            if pgno == 1:
                encrypted = page_data[SALT_SZ : PAGE_SZ - RESERVE_SZ]
                cipher = AES.new(enc_key, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(encrypted)
                return bytes(bytearray(SQLITE_HDR + decrypted + b"\x00" * RESERVE_SZ))
            else:
                encrypted = page_data[: PAGE_SZ - RESERVE_SZ]
                cipher = AES.new(enc_key, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(encrypted)
                return decrypted + b"\x00" * RESERVE_SZ

        def get_key_info(keys, rel_path):
            if isinstance(keys, dict):
                for path_key in keys:
                    if path_key == rel_path or path_key.replace("\\", "/") == rel_path.replace(
                        "\\", "/"
                    ):
                        info = keys[path_key].copy()
                        info["path"] = path_key
                        return info
                return None
            for k in keys:
                if k.get("path") == rel_path or k.get("path", "").replace(
                    "\\", "/"
                ) == rel_path.replace("\\", "/"):
                    return k
                if "keys" in k:
                    for sub in k["keys"]:
                        if sub.get("path") == rel_path:
                            return sub
            return None

        def full_decrypt(db_path, enc_key):
            file_size = os.path.getsize(db_path)
            total_pages = file_size // PAGE_SZ
            chunks = []
            with open(db_path, "rb") as fin:
                for pgno in range(1, total_pages + 1):
                    page = fin.read(PAGE_SZ)
                    if len(page) < PAGE_SZ:
                        if len(page) > 0:
                            page = page + b"\x00" * (PAGE_SZ - len(page))
                        else:
                            break
                    chunks.append(decrypt_page(enc_key, page, pgno))
            return b"".join(chunks)

        stripped_keys = strip_key_metadata(all_keys)
        session_key_info = get_key_info(stripped_keys, os.path.join("session", "session.db"))
        if not session_key_info:
            return {"items": [], "per_contact": per_contact, "error": "session.db key not found"}

        enc_key = bytes.fromhex(session_key_info["enc_key"])
        session_db = os.path.join(copy_db_dir, "session", "session.db")
        if not os.path.exists(session_db):
            return {
                "items": [],
                "per_contact": per_contact,
                "error": "session.db not found in raw_db, run sync_raw_db.py first",
            }

        decrypted_data = full_decrypt(session_db, enc_key)
        import tempfile

        tmp_path = os.path.join(tempfile.gettempdir(), "wechat_work_mode_feed.db")
        with open(tmp_path, "wb") as f:
            f.write(decrypted_data)

        decrypted_dir = cfg.get("decrypted_dir", os.path.join(wechat_decrypt_path, "decrypted"))
        if not os.path.isabs(decrypted_dir):
            decrypted_dir = os.path.join(wechat_decrypt_path, decrypted_dir)
        contact_cache = os.path.join(decrypted_dir, "contact", "contact.db")
        contact_names = {}
        if os.path.exists(contact_cache):
            try:
                cconn = sqlite3.connect(contact_cache)
                for r in cconn.execute(
                    "SELECT username, nick_name, remark FROM contact"
                ).fetchall():
                    uname, nick, remark = r
                    contact_names[uname] = remark if remark else nick if nick else uname
                cconn.close()
            except Exception:
                logger.debug("suppressed exception", exc_info=True)

        items = []
        zstd_dctx = None
        try:
            import zstandard as zstd  # type: ignore[import-untyped]

            zstd_dctx = zstd.ZstdDecompressor()
        except ImportError:
            logger.warning(
                "wechat_work_mode_feed: zstandard not installed; install with `pip install zstandard` for session summary text"
            )
        try:
            with closing(sqlite3.connect(tmp_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT username, unread_count, summary, last_timestamp,
                           last_msg_type, last_msg_sender, last_sender_display_name
                    FROM SessionTable
                    WHERE last_timestamp > 0
                    ORDER BY last_timestamp DESC
                    LIMIT ?
                """,
                    (per_contact * 10,),
                ).fetchall()

                for r in rows:
                    username = r["username"]
                    display = contact_names.get(username, username)
                    summary = r["summary"] or ""
                    if isinstance(summary, bytes):
                        if zstd_dctx is not None:
                            try:
                                summary = zstd_dctx.decompress(summary).decode(
                                    "utf-8", errors="replace"
                                )
                            except Exception:
                                summary = "(compressed)"
                        else:
                            try:
                                summary = summary.decode("utf-8", errors="replace")
                            except Exception:
                                summary = "(compressed; pip install zstandard)"
                    if isinstance(summary, str) and ":\n" in summary:
                        summary = summary.split(":\n", 1)[1]

                    ts = r["last_timestamp"]
                    time_str = (
                        datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
                    )

                    msg_types = {
                        1: "text",
                        3: "image",
                        34: "voice",
                        42: "card",
                        43: "video",
                        47: "sticker",
                        10000: "system",
                    }
                    msg_type = msg_types.get(r["last_msg_type"], f'type={r["last_msg_type"]}')

                    is_group = "@chatroom" in username
                    sender = r["last_msg_sender"] or ""
                    sender_name = r["last_sender_display_name"] or ""
                    sender_display = (
                        contact_names.get(sender, sender_name or sender) if sender else ""
                    )

                    items.append(
                        {
                            "username": username,
                            "display_name": display,
                            "is_group": is_group,
                            "unread_count": r["unread_count"] or 0,
                            "summary": summary,
                            "timestamp": ts,
                            "time_str": time_str,
                            "msg_type": msg_type,
                            "sender": sender,
                            "sender_display": sender_display,
                        }
                    )
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                logger.debug("suppressed exception", exc_info=True)

        return {"items": items[:per_contact], "per_contact": per_contact, "total": len(items)}

    except Exception as e:
        logger.exception("wechat_work_mode_feed error")
        return {"items": [], "per_contact": per_contact, "error": str(e)}


@router.get("/wechat_contacts/decrypt_status")
def wechat_contacts_decrypt_status_compat() -> dict:
    path = os.environ.get("WECHAT_CONTACT_DB_PATH", "").strip()
    exists = bool(path and os.path.isfile(path))
    if not exists:
        base = os.environ.get("WECHAT_DECRYPT_PATH", "").strip()
        if base:
            path = os.path.join(base, "decrypted", "contact", "contact.db")
            exists = os.path.isfile(path)
    return {
        "success": True,
        "plugin_available": True,
        "contact_db_path": path or None,
        "contact_db_exists": exists,
    }


@router.get("/wechat_contacts/search")
def wechat_contacts_search_compat(
    q: str = Query("", description="搜索关键字"),
    keyword: str = Query("", description="与 q 等价"),
) -> dict:
    term = (q or keyword or "").strip().lower()
    if not term:
        return {"success": True, "results": []}
    _migrate_starred_contact_ids()
    hits: list[dict] = []
    for _wxid, c in _STARRED_CONTACTS_DB.items():
        blob = " ".join(
            str(x).lower()
            for x in (c.get("nickname"), c.get("remark"), c.get("wxid"), c.get("type"))
            if x
        )
        if term in blob:
            hits.append(_search_hit_for_frontend(c))
    return {"success": True, "results": hits}


@router.get("/wechat_contacts")
def wechat_contacts_list_compat(
    type: str = Query("all", description="类型: all, contact, group"),
    keyword: str = Query("", description="昵称/备注/微信号筛选"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> dict:
    _migrate_starred_contact_ids()
    all_items = list(_STARRED_CONTACTS_DB.values())
    t = (type or "all").strip().lower()
    if t and t != "all":
        filtered = [c for c in all_items if str(c.get("type", "")).lower() == t]
    else:
        filtered = all_items
    if keyword:
        kw = keyword.lower()
        filtered = [
            c
            for c in filtered
            if kw in str(c.get("nickname", "")).lower()
            or kw in str(c.get("remark", "")).lower()
            or kw in str(c.get("wxid", "")).lower()
        ]
    return {
        "success": True,
        "data": [_starred_row_for_frontend(c) for c in filtered],
        "page": page,
        "per_page": per_page,
    }


@router.post("/wechat_contacts/unstar_all")
async def wechat_contacts_unstar_all_compat() -> dict:
    return await wechat_starred_clear()


@router.post("/wechat_contacts/refresh_messages_cache")
def wechat_contacts_refresh_messages_cache_compat() -> dict:
    return {"success": True, "message": "ok"}


@router.post("/wechat_contacts/refresh_contact_cache")
def wechat_contacts_refresh_contact_cache_compat() -> dict:
    return {
        "success": True,
        "message": "ok",
        "data": {"sync": {"success": True, "message": "占位"}},
    }


@router.post("/wechat_contacts")
def wechat_contacts_create_compat(body: dict = Body(default_factory=dict)) -> dict:
    wxid = str(body.get("wechat_id") or body.get("wxid") or "").strip()
    if not wxid:
        raise HTTPException(status_code=400, detail="wechat_id 不能为空")
    nickname = str(body.get("contact_name") or body.get("nickname") or "").strip()
    remark = str(body.get("remark") or "").strip()
    contact_type = (
        str(body.get("contact_type") or body.get("type") or "contact").strip() or "contact"
    )
    global _STARRED_NEXT_ID
    _migrate_starred_contact_ids()
    cid = _STARRED_NEXT_ID
    _STARRED_NEXT_ID += 1
    contact = {
        "id": cid,
        "type": contact_type,
        "nickname": nickname,
        "remark": remark,
        "wxid": wxid,
        "starred": True,
    }
    _STARRED_CONTACTS_DB[wxid] = contact
    return {"success": True, "message": "ok", "data": {"id": cid}}


@router.get("/wechat_contacts/starred")
def wechat_starred_list(
    type: str = Query(default="all", description="类型筛选: all, contact, group"),
    keyword: str = Query(default="", description="昵称/备注筛选关键字"),
) -> dict:
    _migrate_starred_contact_ids()
    all_items = list(_STARRED_CONTACTS_DB.values())

    if type and type != "all":
        filtered = [c for c in all_items if c.get("type", "").lower() == type.lower()]
    else:
        filtered = all_items

    if keyword:
        kw = keyword.lower()
        filtered = [
            c
            for c in filtered
            if kw in str(c.get("nickname", "")).lower()
            or kw in str(c.get("remark", "")).lower()
            or kw in str(c.get("wxid", "")).lower()
        ]

    return {
        "success": True,
        "data": filtered,
        "total": len(filtered),
        "filter": {"type": type, "keyword": keyword},
    }


@router.delete("/wechat_contacts/starred/{wxid}")
def wechat_starred_delete(wxid: str) -> dict:
    if wxid in _STARRED_CONTACTS_DB:
        del _STARRED_CONTACTS_DB[wxid]
        return {"success": True, "message": f"已删除星标联系人 {wxid}"}
    return {"success": False, "message": f"星标联系人 {wxid} 不存在"}


@router.delete("/wechat_contacts/starred")
def wechat_starred_clear() -> dict:
    count = len(_STARRED_CONTACTS_DB)
    _STARRED_CONTACTS_DB.clear()
    return {"success": True, "message": f"已清除 {count} 个星标"}


@router.post("/wechat_contacts/starred")
def wechat_starred_add(body: dict = Body(...)) -> dict:
    global _STARRED_NEXT_ID
    wxid = str(body.get("wxid") or body.get("wechat_id") or "").strip()
    if not wxid:
        raise HTTPException(status_code=400, detail="wxid 不能为空")

    contact_type = body.get("type") or body.get("contact_type") or "contact"
    nickname = body.get("nickname") or body.get("contact_name") or ""
    remark = body.get("remark", "")

    _migrate_starred_contact_ids()
    cid = _STARRED_NEXT_ID
    _STARRED_NEXT_ID += 1
    contact = {
        "id": cid,
        "type": contact_type,
        "nickname": nickname,
        "remark": remark,
        "wxid": wxid,
        "starred": True,
    }
    _STARRED_CONTACTS_DB[wxid] = contact
    return {"success": True, "data": contact}


@router.delete("/wechat_contacts/{contact_id}")
def wechat_contacts_delete_compat(contact_id: str) -> dict:
    _migrate_starred_contact_ids()
    for wxid, c in list(_STARRED_CONTACTS_DB.items()):
        if str(c.get("id")) == str(contact_id):
            del _STARRED_CONTACTS_DB[wxid]
            return {"success": True, "message": "已删除"}
    return {"success": False, "message": "联系人不存在"}


@router.put("/wechat_contacts/{contact_id}")
def wechat_contacts_update_compat(contact_id: str, body: dict = Body(default_factory=dict)) -> dict:
    _migrate_starred_contact_ids()
    for _wxid, c in _STARRED_CONTACTS_DB.items():
        if str(c.get("id")) == str(contact_id):
            if "contact_name" in body:
                c["nickname"] = str(body.get("contact_name") or "")
            if "remark" in body:
                c["remark"] = str(body.get("remark") or "")
            if "wechat_id" in body:
                c["wxid"] = str(body.get("wechat_id") or "")
            if "contact_type" in body:
                c["type"] = str(body.get("contact_type") or "contact")
            return {"success": True, "data": _starred_row_for_frontend(c)}
    return {"success": False, "message": "联系人不存在"}


@router.get("/wechat_contacts/{contact_id}/context")
def wechat_contacts_context_compat(contact_id: str) -> dict:
    _ = contact_id
    return {"success": True, "messages": []}


@router.post("/wechat_contacts/{contact_id}/refresh_messages")
def wechat_contacts_refresh_messages_compat(contact_id: str) -> dict:
    _ = contact_id
    return {"success": True, "message": "FHD 精简后端未实现消息库同步"}
