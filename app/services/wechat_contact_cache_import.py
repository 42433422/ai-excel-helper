"""
从微信解密库同步联系人到 ``WechatContact`` 表（归档 ``refresh_contact_cache_compat`` 逻辑）。

供原生 FastAPI 路由调用，避免依赖 HTTP 请求上下文。
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime
from typing import Any

from app.db.models import WechatContact
from app.db.session import get_db
from app.utils.external_sqlite import sqlite_conn
from app.utils.path_utils import get_resource_path

logger = logging.getLogger(__name__)


def _resolve_wechat_decrypt_dir() -> str | None:
    """定位 wechat-decrypt 工具目录(含 config.py / key_utils.py / decrypt_db.py)。

    历史原因有多个可能路径:
    - ``<repo>/resources/wechat-decrypt/`` (约定落点,但常只存 raw_db)
    - ``<repo>/XCAGI/resources/wechat-decrypt/`` (发行子树)
    - ``<repo>/XCAGI/wechat-decrypt/`` (便携副本)
    - ``<repo>/wechat-decrypt/`` (少数老部署)

    按优先级挑第一个**包含 ``config.py``** 的目录返回,都找不到则返回 None。
    """
    import pathlib

    repo_root = pathlib.Path(get_resource_path()).parent  # <repo>
    candidates = [
        pathlib.Path(get_resource_path("wechat-decrypt")),
        repo_root / "XCAGI" / "resources" / "wechat-decrypt",
        repo_root / "XCAGI" / "wechat-decrypt",
        repo_root / "wechat-decrypt",
    ]
    for p in candidates:
        if (p / "config.py").is_file():
            return str(p)
    return None


def ensure_decrypted_wechat_dbs() -> dict[str, Any]:
    """
    确保微信数据库已同步并解密（归档 ``_ensure_decrypted_db``）。
    返回 {"success": bool, "message": str, ...}

    当 ``success=False`` 且 ``reason == "not_configured"`` 时,调用方应使用 HTTP 503
    而非 500 —— 这表示"未配置 WeChat 解密环境",不是服务器故障。
    """
    try:
        import glob as glob_module
        import shutil
        import sys

        wechat_decrypt_path = _resolve_wechat_decrypt_dir()
        if wechat_decrypt_path is None:
            return {
                "success": False,
                "reason": "not_configured",
                "message": (
                    "未找到 wechat-decrypt 工具(config.py)。请放置到下列任一目录:"
                    " resources/wechat-decrypt/、XCAGI/resources/wechat-decrypt/、"
                    "XCAGI/wechat-decrypt/ 或 wechat-decrypt/。"
                ),
            }
        if wechat_decrypt_path not in sys.path:
            sys.path.insert(0, wechat_decrypt_path)

        from key_utils import get_key_info, strip_key_metadata

        from config import load_config

        cfg = load_config()
        raw_db_dir = os.path.join(wechat_decrypt_path, "raw_db")
        decrypted_dir = cfg.get("decrypted_dir", os.path.join(wechat_decrypt_path, "decrypted"))
        keys_file = cfg.get("keys_file", os.path.join(wechat_decrypt_path, "all_keys.json"))
        db_dir = cfg.get("db_dir", "")

        if not db_dir or not os.path.isdir(db_dir):
            return {
                "success": False,
                "reason": "not_configured",
                "message": f"微信数据目录不存在: {db_dir or '(未配置 db_dir)'}",
            }

        source_sections = ("message", "contact")
        for section in source_sections:
            raw_section_dir = os.path.join(raw_db_dir, section)
            src_section_dir = os.path.join(db_dir, section)
            os.makedirs(raw_section_dir, exist_ok=True)
            if os.path.exists(src_section_dir):
                for f in glob_module.glob(os.path.join(src_section_dir, "*.db")):
                    if f.endswith("-wal") or f.endswith("-shm"):
                        continue
                    rel = os.path.relpath(f, src_section_dir)
                    dst = os.path.join(raw_section_dir, rel)
                    try:
                        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(f):
                            shutil.copy2(f, dst)
                    except Exception as copy_err:
                        logger.warning(
                            "[WeChat] 复制原始库失败 section=%s file=%s err=%s",
                            section,
                            f,
                            copy_err,
                        )
                        continue

        if not os.path.exists(keys_file):
            return {
                "success": False,
                "reason": "not_configured",
                "message": "密钥文件不存在，请先运行 wechat-decrypt 获取密钥",
            }

        with open(keys_file, encoding="utf-8") as f:
            keys = json.load(f)
        keys = strip_key_metadata(keys)
        if not keys:
            return {
                "success": False,
                "reason": "not_configured",
                "message": "密钥文件为空或无效",
            }

        decrypt_counts = {"message": 0, "contact": 0}
        for section in source_sections:
            raw_section_dir = os.path.join(raw_db_dir, section)
            decrypted_section_dir = os.path.join(decrypted_dir, section)
            os.makedirs(decrypted_section_dir, exist_ok=True)

            raw_files = glob_module.glob(os.path.join(raw_section_dir, "*.db"))
            for raw_path in raw_files:
                rel = os.path.relpath(raw_path, raw_section_dir)
                decrypted_path = os.path.join(decrypted_section_dir, rel)

                key_info = get_key_info(keys, os.path.join(section, rel))
                if not key_info:
                    continue

                need_decrypt = not os.path.exists(decrypted_path)
                if not need_decrypt:
                    try:
                        if os.path.getmtime(decrypted_path) < os.path.getmtime(raw_path):
                            need_decrypt = True
                    except Exception:
                        need_decrypt = True

                if need_decrypt:
                    try:
                        enc_key = bytes.fromhex(key_info["enc_key"])
                        from decrypt_db import decrypt_database

                        if decrypt_database(raw_path, decrypted_path, enc_key):
                            decrypt_counts[section] += 1
                    except Exception as dec_err:
                        logger.warning(
                            "[WeChat] 解密失败 section=%s raw=%s err=%s",
                            section,
                            raw_path,
                            dec_err,
                        )
                        continue

        total = decrypt_counts["message"] + decrypt_counts["contact"]
        return {
            "success": True,
            "message": (
                f"已同步并解密 {total} 个数据库"
                f"（message: {decrypt_counts['message']}，contact: {decrypt_counts['contact']}）"
            ),
            "decrypted": decrypt_counts,
        }

    except ModuleNotFoundError as e:
        logger.error("[WeChat] 依赖的 wechat-decrypt 模块缺失: %s", e)
        return {
            "success": False,
            "reason": "not_configured",
            "message": f"wechat-decrypt 工具模块缺失: {e}。请确认工具目录包含 config.py / key_utils.py / decrypt_db.py。",
        }
    except Exception as e:
        logger.error(
            "[WeChat] ensure_decrypted_wechat_dbs 错误: %s\n%s", str(e), traceback.format_exc()
        )
        return {"success": False, "message": f"同步解密失败: {str(e)}"}


def refresh_wechat_contacts_from_decrypt() -> tuple[dict[str, Any], int]:
    """
    从解密库导入联系人到 ORM 表。
    返回 (payload, http_status)。
    """
    try:
        sync_result = ensure_decrypted_wechat_dbs()
        if not sync_result.get("success"):
            # 配置/资源缺失 -> 503(Service Unavailable),前端可识别为"未配置"而非崩溃
            status_code = 503 if sync_result.get("reason") == "not_configured" else 500
            return {
                "success": False,
                "reason": sync_result.get("reason"),
                "message": sync_result.get("message", "同步解密失败"),
            }, status_code

        # 定位解密后的库根目录:优先使用本次 ensure 成功定位到的工具目录
        wechat_decrypt_path = _resolve_wechat_decrypt_dir() or get_resource_path("wechat-decrypt")

        rows: list[Any] = []
        source_desc = "contact.db"
        contact_db_path = os.path.join(wechat_decrypt_path, "decrypted", "contact", "contact.db")
        if os.path.exists(contact_db_path):
            with sqlite_conn(contact_db_path) as conn:
                cur = conn.cursor()
                table_exists = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='contact'"
                ).fetchone()
                if table_exists:
                    col_rows = cur.execute("PRAGMA table_info(contact)").fetchall()
                    cols = {str(r[1]) for r in col_rows if len(r) >= 2}

                    select_cols = ["username"]
                    select_cols.append("nick_name" if "nick_name" in cols else "'' AS nick_name")
                    select_cols.append("remark" if "remark" in cols else "'' AS remark")
                    select_cols.append(
                        "is_in_chat_room" if "is_in_chat_room" in cols else "0 AS is_in_chat_room"
                    )

                    where_clause = "WHERE delete_flag = 0" if "delete_flag" in cols else ""
                    sql = f"SELECT {', '.join(select_cols)} FROM contact {where_clause}"
                    rows = cur.execute(sql).fetchall()

        if not rows:
            msg_db_path = os.path.join(wechat_decrypt_path, "decrypted", "message", "message_0.db")
            if os.path.exists(msg_db_path):
                with sqlite_conn(msg_db_path) as conn:
                    cur = conn.cursor()
                    table_exists = cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='Name2Id'"
                    ).fetchone()
                    if table_exists:
                        source_desc = "message_0.db/Name2Id"
                        rows = cur.execute(
                            "SELECT user_name, '', '', is_session FROM Name2Id"
                        ).fetchall()

        if not rows:
            return {
                "success": False,
                "message": "未找到可导入的联系人源（contact.db 与 Name2Id 均不可用）",
                "skipped": True,
            }, 200

        imported = 0
        updated = 0
        skipped = 0
        now = datetime.now()

        with get_db() as db:
            # 修正 PostgreSQL 序列漂移:确保 wechat_contacts_id_seq 的 last_value 不落后
            # 于表内最大 id。历史迁移(SQLite -> PG,或显式 id 的 INSERT)会留下漂移,
            # 导致后续新增触发 duplicate key violates "wechat_contacts_pkey"。
            try:
                from sqlalchemy import text as _sa_text

                _dialect = db.bind.dialect.name if db.bind is not None else ""
                if _dialect == "postgresql":
                    db.execute(
                        _sa_text(
                            "SELECT setval("
                            "  pg_get_serial_sequence('wechat_contacts', 'id'),"
                            "  COALESCE((SELECT MAX(id) FROM wechat_contacts), 0) + 1,"
                            "  false"
                            ")"
                        )
                    )
            except Exception as seq_err:
                logger.warning("[WeChat] 调整 wechat_contacts_id_seq 失败(忽略): %s", seq_err)

            # 去掉 10000 的上限,联系人可能更多
            existing_contacts = db.query(WechatContact).all()
            existing_by_wechat_id: dict[str, WechatContact] = {}
            for c in existing_contacts:
                key = (c.wechat_id or "").strip()
                if key:
                    existing_by_wechat_id[key] = c

            for row in rows:
                username = (row[0] or "").strip()
                nick_name = (row[1] or "").strip()
                remark = (row[2] or "").strip()
                is_in_chat_room = str(row[3] or "0").strip()

                if not username:
                    skipped += 1
                    continue

                contact_type = (
                    "group" if (is_in_chat_room == "1" or "@chatroom" in username) else "contact"
                )
                contact_name = nick_name or remark or username

                existing = existing_by_wechat_id.get(username)
                if existing:
                    existing.contact_name = contact_name
                    existing.remark = remark
                    existing.contact_type = contact_type
                    existing.is_active = 1
                    existing.updated_at = now
                    updated += 1
                    continue

                db.add(
                    WechatContact(
                        contact_name=contact_name,
                        remark=remark,
                        wechat_id=username,
                        contact_type=contact_type,
                        is_active=1,
                        is_starred=0,
                    )
                )
                imported += 1

            db.commit()

        total = imported + updated
        return {
            "success": True,
            "message": f"联系人缓存已刷新（来源：{source_desc}）：新增 {imported}，更新 {updated}，跳过 {skipped}",
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": total,
        }, 200
    except Exception as e:
        logger.exception("refresh_wechat_contacts_from_decrypt failed: %s", e)
        return {"success": False, "message": f"刷新失败：{str(e)}"}, 500


def wechat_message_source_size_payload() -> tuple[dict[str, Any], int]:
    """归档 ``message_source_size``：汇总 context.message_count。"""
    try:
        from app.db.models import WechatContactContext
        from app.services.unified_query_service import query_service

        rows = query_service.get_all(WechatContactContext)
        size = 0
        for r in rows:
            try:
                size += int(r.message_count or 0)
            except Exception:
                continue
        return {"success": True, "size": size}, 200
    except Exception as e:
        return {"success": False, "message": f"获取失败：{str(e)}", "size": 0}, 500
