# -*- coding: utf-8 -*-
"""
微信联系人路由（兼容旧版前端路径）

提供 /api/wechat_contacts 路径的兼容接口
"""

import json
import logging
import os

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from app.application import WechatContactApplicationService, get_wechat_contact_app_service
from app.utils.external_sqlite import sqlite_conn
from app.utils.json_safe import json_safe

wechat_contacts_bp = Blueprint("wechat_contacts", __name__, url_prefix="/api/wechat_contacts")
logger = logging.getLogger(__name__)


def get_wechat_contact_service():
    return get_wechat_contact_app_service()


@wechat_contacts_bp.route("", methods=["GET"])
@swag_from({
    "summary": "获取微信联系人列表（兼容旧路径）",
    "description": "获取微信联系人列表，支持按类型筛选",
    "parameters": [
        {
            "name": "type",
            "in": "query",
            "type": "string",
            "description": "联系人类型（contact/group/all），默认 all"
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "description": "返回数量限制，默认 100"
        }
    ],
    "responses": {
        "200": {
            "description": "查询成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "total": {"type": "integer"}
                }
            }
        }
    }
})
def wechat_contacts_list_compat():
    """获取微信联系人列表（兼容旧路径）"""
    try:
        contact_type = request.args.get("type", "all")
        limit = request.args.get("limit", 100, type=int)

        service = get_wechat_contact_service()
        contacts = service.get_contacts(
            contact_type=contact_type,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": contacts,
            "total": len(contacts)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/ensure_contact_cache", methods=["POST", "GET"])
@swag_from({
    "summary": "确保联系人缓存",
    "description": "确保微信联系人缓存已初始化",
    "responses": {
        "200": {
            "description": "操作成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        }
    }
})
def ensure_contact_cache():
    """确保联系人缓存已初始化"""
    try:
        # 与旧页面行为对齐：进入页面时即尝试从解密库导入一次联系人缓存。
        return refresh_contact_cache_compat()
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"检查缓存失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/search", methods=["GET"])
@swag_from({
    "summary": "搜索联系人",
    "description": "根据关键词搜索微信联系人",
    "parameters": [
        {
            "name": "q",
            "in": "query",
            "type": "string",
            "description": "搜索关键词",
            "required": True
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "description": "返回数量限制，默认 20"
        }
    ],
    "responses": {
        "200": {
            "description": "查询成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "results": {"type": "array"}
                }
            }
        }
    }
})
def wechat_contacts_search():
    """搜索联系人（在所有联系人中搜索，用于添加星标）"""
    try:
        query = request.args.get("q", "")
        limit = request.args.get("limit", 20, type=int)

        service = get_wechat_contact_service()
        # 搜索时在所有联系人中搜索，不限制类型
        contacts = service.get_contacts(
            keyword=query,
            contact_type=None,  # 不限制类型，搜索所有联系人
            limit=limit
        )

        # 转换为前端期望的格式
        results = []
        for c in contacts:
            results.append({
                "display_name": c.get("contact_name"),
                "nick_name": c.get("contact_name"),
                "username": c.get("wechat_id"),
                "remark": c.get("remark"),
                "already_starred": c.get("is_starred") == 1
            })

        return jsonify({
            "success": True,
            "results": results
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"搜索失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/unstar_all", methods=["POST"])
@swag_from({
    "summary": "取消所有星标（兼容旧路径）",
    "description": "取消所有联系人的星标状态",
    "responses": {
        "200": {
            "description": "操作成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        }
    }
})
def wechat_contacts_unstar_all():
    """取消所有联系人星标（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        result = service.unstar_all()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"操作失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>", methods=["GET"])
def wechat_contact_get_compat(contact_id):
    """获取单个联系人（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        contact = service.get_contact_by_id(contact_id)

        if contact:
            return jsonify({
                "success": True,
                "data": contact
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "联系人不存在"
            }), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>", methods=["PUT"])
def wechat_contact_update_compat(contact_id):
    """更新联系人（兼容旧路径）"""
    try:
        data = request.get_json() or {}
        contact_name = data.get("contact_name", "").strip()
        remark = data.get("remark", "").strip()
        wechat_id = data.get("wechat_id", "").strip()
        contact_type = data.get("contact_type")
        is_starred = data.get("is_starred")

        service = get_wechat_contact_service()
        result = service.update_contact(
            contact_id=contact_id,
            contact_name=contact_name if contact_name else None,
            remark=remark if remark else None,
            wechat_id=wechat_id if wechat_id else None,
            contact_type=contact_type,
            is_starred=is_starred
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>", methods=["DELETE"])
def wechat_contact_delete_compat(contact_id):
    """删除联系人（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        result = service.delete_contact(contact_id)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>/context", methods=["GET"])
def wechat_contact_context_compat(contact_id):
    """获取联系人聊天上下文（兼容旧路径）"""
    try:
        service = get_wechat_contact_service()
        messages = service.get_contact_context(contact_id)

        return jsonify({
            "success": True,
            "messages": messages,
            "count": len(messages)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500


@wechat_contacts_bp.route("/<int:contact_id>/refresh_messages", methods=["POST"])
@swag_from({
    "summary": "刷新联系人聊天记录",
    "description": "从微信数据库拉取最新消息并保存到聊天上下文",
    "parameters": [
        {
            "name": "contact_id",
            "in": "path",
            "type": "integer",
            "description": "联系人 ID",
            "required": True
        }
    ],
    "requestBody": {
        "description": "可选的请求体参数",
        "required": False,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "拉取消息数量限制，默认 50",
                            "default": 50
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "刷新成功",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "count": {"type": "integer"}
                }
            }
        },
        "400": {
            "description": "刷新失败，联系人不存在或参数错误"
        },
        "500": {
            "description": "服务器内部错误"
        }
    }
})
def wechat_contact_refresh_messages_compat(contact_id):
    """刷新联系人聊天记录（兼容旧路径）"""
    try:
        import json
        import os

        from app.db.models import WechatContact, WechatContactContext
        from app.db.session import get_db
        from app.services.unified_query_service import query_service
        from app.utils.path_utils import get_resource_path

        contact = query_service.get_first(WechatContact, id=contact_id, is_active=1)
        if not contact:
            return jsonify({"success": False, "message": "联系人不存在", "count": 0}), 400

        wechat_id = contact.wechat_id or ""
        if not wechat_id:
            return jsonify({"success": False, "message": "联系人无微信号", "count": 0}), 400

        with get_db() as db:
            try:
                import sys

                from app.utils.path_utils import get_resource_path

                wechat_cv_path = get_resource_path("wechat_cv")
                if os.path.isdir(wechat_cv_path) and wechat_cv_path not in sys.path:
                    sys.path.insert(0, wechat_cv_path)

                wechat_decrypt_path = get_resource_path("wechat-decrypt")
                if wechat_decrypt_path not in sys.path:
                    sys.path.insert(0, wechat_decrypt_path)

                from wechat_db_read import get_messages_for_contact
            except Exception as e:
                return jsonify({"success": False, "message": f"无法导入消息读取模块: {e}", "count": 0}), 500

            sync_result = _ensure_decrypted_db()
            if not sync_result.get("success"):
                return jsonify({"success": False, "message": sync_result.get("message", "同步失败"), "count": 0}), 500

            decrypted_msg_dir = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message")
            msg_db_path = os.path.join(decrypted_msg_dir, "message_0.db")
            if not os.path.exists(msg_db_path):
                return jsonify({"success": False, "message": f"解密后的数据库不存在: {msg_db_path}", "count": 0}), 500

            all_messages = _query_messages_from_hash_tables(msg_db_path, wechat_id, limit=50, search_in_content=True)
            import logging
            logging.getLogger(__name__).info(f"[DEBUG] _query_messages_from_hash_tables returned {len(all_messages)} messages for wechat_id={wechat_id}")

            if not all_messages:
                return jsonify({"success": True, "message": "无聊天记录", "count": 0}), 200

            ctx = query_service.get_first(WechatContactContext, contact_id=contact_id)
            if ctx:
                ctx.wechat_id = wechat_id
                ctx.context_json = json.dumps(all_messages, ensure_ascii=False)
                ctx.message_count = len(all_messages)
            else:
                ctx = WechatContactContext(
                    contact_id=contact_id,
                    wechat_id=wechat_id,
                    context_json=json.dumps(all_messages, ensure_ascii=False),
                    message_count=len(all_messages)
                )
                db.add(ctx)
            db.commit()

            return jsonify({"success": True, "message": f"已刷新 {len(all_messages)} 条聊天记录", "count": len(all_messages)}), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"刷新失败：{str(e)}",
            "count": 0
        }), 500


def _query_messages_by_content(msg_db_path, wechat_id, limit=50):
    """在消息内容中搜索包含 wechat_id 的消息，或包含纯文本消息"""
    import sqlite3
    all_messages = []
    try:
        sys.path.insert(0, get_resource_path("wechat-decrypt"))
        from mcp_server import _decompress_content
    except Exception:
        _decompress_content = None

    try:
        with sqlite_conn(msg_db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
            tables = [row[0] for row in cur.fetchall()]

            for table in tables:
                try:
                    cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] ORDER BY create_time DESC LIMIT 2000")
                    rows = cur.fetchall()
                    for row in rows:
                        raw_content = row[0]
                        ct = row[1]
                        if not raw_content:
                            continue
                        content = _decompress_content(raw_content, ct) if _decompress_content else raw_content
                        if isinstance(content, bytes):
                            content = content.decode('utf-8', errors='replace') if content else ''
                        content = (content or "").strip()
                        if not content:
                            continue
                        if wechat_id in content or (content.startswith('<') and wechat_id in content):
                            all_messages.append({"role": "other", "text": content})
                        if len(all_messages) >= limit:
                            break
                    if len(all_messages) >= limit:
                        break
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"查询消息失败: {e}")

    if len(all_messages) > limit:
        all_messages = all_messages[:limit]
    return all_messages


def _get_contact_numeric_id(wechat_id):
    """从 contact.db 获取联系人的 numeric id"""
    import sqlite3
    try:
        contact_db = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "contact", "contact.db")
        if not os.path.exists(contact_db):
            return None
        with sqlite_conn(contact_db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM contact WHERE username = ?", (wechat_id,))
            row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _query_messages_by_numeric_id(msg_db_path, numeric_id, wechat_id, limit=50):
    """通过 numeric_id 查询消息，如果没有则回退到内容搜索"""
    import sqlite3
    all_messages = []
    try:
        sys.path.insert(0, get_resource_path("wechat-decrypt"))
        from mcp_server import _decompress_content
    except Exception:
        _decompress_content = None

    def decompress(raw, ct):
        if not raw:
            return ""
        if _decompress_content:
            result = _decompress_content(raw, ct)
            if isinstance(result, bytes):
                return result.decode('utf-8', errors='replace')
            return result or ""
        return raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw or ""

    try:
        with sqlite_conn(msg_db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
            tables = [row[0] for row in cur.fetchall()]

            if numeric_id:
                for table in tables:
                    try:
                        cur.execute(f"PRAGMA table_info([{table}])")
                        cols = [c[1] for c in cur.fetchall()]
                        if 'real_sender_id' not in cols:
                            continue

                        cur.execute(f"SELECT message_content, WCDB_CT_message_content, create_time FROM [{table}] WHERE real_sender_id = ? ORDER BY create_time DESC LIMIT {limit}", [numeric_id])
                        rows = cur.fetchall()
                        for row in rows:
                            content = decompress(row[0], row[1]).strip()
                            if not content:
                                continue
                            all_messages.append({"role": "other", "text": content})
                            if len(all_messages) >= limit:
                                break
                        if all_messages:
                            break
                    except Exception:
                        continue
    except Exception as e:
        logger.warning(f"查询哈希表消息失败: {e}")

    if len(all_messages) > limit:
        all_messages = all_messages[:limit]
    return all_messages


def _query_messages_from_hash_tables(msg_db_path, talker, limit=50, search_in_content=False):
    """查询哈希表格式的微信消息数据库（Msg_<hash> 表）

    表名 = Msg_<MD5(talker)>
    """
    import sys
    import sqlite3
    import hashlib
    import logging
    from app.utils.path_utils import get_resource_path
    logger = logging.getLogger(__name__)
    all_messages = []
    try:
        sys.path.insert(0, get_resource_path("wechat-decrypt"))
        from mcp_server import _decompress_content
    except Exception as e:
        logger.warning(f"[DEBUG] Failed to import _decompress_content: {e}")
        _decompress_content = None

    try:
        talker_hash = hashlib.md5(talker.encode('utf-8')).hexdigest()
        table_name = f"Msg_{talker_hash}"
        logger.info(f"[DEBUG] Looking for table: {table_name}")

        with sqlite_conn(msg_db_path) as conn:
            cur = conn.cursor()

            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cur.fetchone():
                logger.warning(f"[DEBUG] Table {table_name} does not exist")
                return []

            cur.execute(f"PRAGMA table_info([{table_name}])")
            cols = [c[1] for c in cur.fetchall()]
            content_col = 'content' if 'content' in cols else 'message_content'
            time_col = 'createTime' if 'createTime' in cols else 'create_time'
            ct_col = 'WCDB_CT_message_content' if 'WCDB_CT_message_content' in cols else None
            is_send_col = 'isSend' if 'isSend' in cols else None

            # 与 time_col 一致（曾硬编码 create_time，在仅含 createTime 的 WCDB 表上会 SQL 报错）
            sql = f"SELECT {content_col}, {is_send_col or '0'}, {time_col}, {ct_col or 'NULL'} FROM [{table_name}] ORDER BY [{time_col}] DESC LIMIT {limit}"
            logger.info(f"[DEBUG] Executing: {sql}")
            cur.execute(sql)
            rows = cur.fetchall()
            logger.info(f"[DEBUG] Got {len(rows)} rows from {table_name}")

            for row in rows:
                raw_content = row[0]
                ct = row[3] if len(row) > 3 else None
                if _decompress_content:
                    content = _decompress_content(raw_content, ct)
                else:
                    content = raw_content
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='replace') if content else ''
                elif not isinstance(content, str):
                    content = str(content) if content is not None else ""
                content = (content or "").strip()
                if not content:
                    continue
                role = "other" if (is_send_col and row[1] == 0) else "self"
                all_messages.append({"role": role, "text": content})
                if len(all_messages) >= limit:
                    break
    except Exception as e:
        logger.warning(f"[DEBUG] Exception in _query_messages_from_hash_tables: {e}")

    if len(all_messages) > limit:
        all_messages = all_messages[:limit]
    return all_messages


def _ensure_decrypted_db():
    """
    确保微信数据库已同步并解密。
    1. 从原始目录复制到 raw_db/
    2. 用密钥解密到 decrypted/
    返回 {"success": True/False, "message": str}
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    try:
        import glob as glob_module
        import os
        import shutil
        import sys

        from app.utils.path_utils import get_resource_path

        wechat_decrypt_path = get_resource_path("wechat-decrypt")
        if wechat_decrypt_path not in sys.path:
            sys.path.insert(0, wechat_decrypt_path)

        from config import load_config
        from key_utils import get_key_info, strip_key_metadata

        cfg = load_config()
        raw_db_dir = os.path.join(wechat_decrypt_path, "raw_db")
        decrypted_dir = cfg.get("decrypted_dir", os.path.join(wechat_decrypt_path, "decrypted"))
        keys_file = cfg.get("keys_file", os.path.join(wechat_decrypt_path, "all_keys.json"))
        db_dir = cfg.get("db_dir", "")

        logger.info(f"[WeChat] db_dir: {db_dir}")
        logger.info(f"[WeChat] keys_file: {keys_file}, exists: {os.path.exists(keys_file)}")
        logger.info(f"[WeChat] raw_db_dir: {raw_db_dir}")
        logger.info(f"[WeChat] decrypted_dir: {decrypted_dir}")

        if not db_dir or not os.path.isdir(db_dir):
            return {"success": False, "message": f"微信数据目录不存在: {db_dir}"}

        # 同步原始库：message + contact（按 mtime 增量复制，避免“文件数不变但内容已变更”漏同步）
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
                        logger.warning("[WeChat] 复制原始库失败 section=%s file=%s err=%s", section, f, copy_err)
                        continue

        if not os.path.exists(keys_file):
            return {"success": False, "message": "密钥文件不存在，请先运行 wechat-decrypt 获取密钥"}

        with open(keys_file, "r", encoding="utf-8") as f:
            keys = json.load(f)
        keys = strip_key_metadata(keys)
        if not keys:
            return {"success": False, "message": "密钥文件为空或无效"}

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

    except Exception as e:
        logger.error(f"[WeChat] _ensure_decrypted_db 错误: {str(e)}\n{traceback.format_exc()}")
        return {"success": False, "message": f"同步解密失败: {str(e)}"}


@wechat_contacts_bp.route("/message_source_size", methods=["GET"])
def message_source_size():
    """
    工作模式：获取消息源大小（用于前端判断是否需要刷新缓存）
    返回：{success:true, size:<int>}
    """
    try:
        # 以所有 context 的 message_count 近似（保持兼容：这里走原 DB 查询）
        from app.db.models import WechatContactContext
        from app.db.session import get_db
        from app.services.unified_query_service import query_service

        rows = query_service.get_all(WechatContactContext)
        size = 0
        for r in rows:
            try:
                size += int(r.message_count or 0)
            except Exception as e:
                logger.debug(f"计算消息大小跳过一行: {e}")
        return jsonify({"success": True, "size": size}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"获取失败：{str(e)}", "size": 0}), 500


@wechat_contacts_bp.route("/refresh_messages_cache", methods=["POST"])
def refresh_messages_cache():
    """
    工作模式：刷新消息缓存
    触发一次“复制原库+解密”，确保 message/contact 解密产物是最新。
    """
    try:
        sync_result = _ensure_decrypted_db()
        status = 200 if sync_result.get("success") else 500
        return jsonify(sync_result), status
    except Exception as e:
        return jsonify({"success": False, "message": f"刷新失败：{str(e)}"}), 500


@wechat_contacts_bp.route("/refresh_contact_cache", methods=["POST"])
def refresh_contact_cache_compat():
    """
    兼容旧前端：刷新联系人缓存

    从微信解密库导入联系人到本地 wechat_contacts 表（保留既有星标状态）。
    """
    try:
        import sqlite3
        from datetime import datetime

        from app.db.models import WechatContact
        from app.db.session import get_db
        from app.utils.path_utils import get_resource_path

        sync_result = _ensure_decrypted_db()
        if not sync_result.get("success"):
            return jsonify({"success": False, "message": sync_result.get("message", "同步解密失败")}), 500

        rows = []
        source_desc = "contact.db"
        contact_db_path = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "contact", "contact.db")
        if os.path.exists(contact_db_path):
            with sqlite_conn(contact_db_path) as conn:
                cur = conn.cursor()

                # 兼容不同版本的 contact.db 字段
                table_exists = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='contact'"
                ).fetchone()
                if table_exists:
                    col_rows = cur.execute("PRAGMA table_info(contact)").fetchall()
                    cols = {str(r[1]) for r in col_rows if len(r) >= 2}

                    select_cols = ["username"]
                    select_cols.append("nick_name" if "nick_name" in cols else "'' AS nick_name")
                    select_cols.append("remark" if "remark" in cols else "'' AS remark")
                    select_cols.append("is_in_chat_room" if "is_in_chat_room" in cols else "0 AS is_in_chat_room")

                    where_clause = "WHERE delete_flag = 0" if "delete_flag" in cols else ""
                    sql = f"SELECT {', '.join(select_cols)} FROM contact {where_clause}"
                    rows = cur.execute(sql).fetchall()

        # 某些环境只有 message_0.db（没有 decrypted/contact/contact.db），
        # 这里回退从 Name2Id 导入基础联系人（至少可按微信号搜索/星标）。
        if not rows:
            msg_db_path = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message", "message_0.db")
            if os.path.exists(msg_db_path):
                with sqlite_conn(msg_db_path) as conn:
                    cur = conn.cursor()
                    table_exists = cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='Name2Id'"
                    ).fetchone()
                    if table_exists:
                        source_desc = "message_0.db/Name2Id"
                        rows = cur.execute("SELECT user_name, '', '', is_session FROM Name2Id").fetchall()

        if not rows:
            return jsonify({
                "success": False,
                "message": "未找到可导入的联系人源（contact.db 与 Name2Id 均不可用）",
            }), 404

        imported = 0
        updated = 0
        skipped = 0
        now = datetime.now()

        from app.db.models import WechatContact

        with get_db() as db:
            existing_contacts = db.query(WechatContact).limit(10000).all()
            existing_by_wechat_id = {}
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

                contact_type = "group" if (is_in_chat_room == "1" or "@chatroom" in username) else "contact"
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
        return jsonify({
            "success": True,
            "message": f"联系人缓存已刷新（来源：{source_desc}）：新增 {imported}，更新 {updated}，跳过 {skipped}",
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": total,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"刷新失败：{str(e)}"}), 500


@wechat_contacts_bp.route("/work_mode_feed", methods=["GET"])
def work_mode_feed():
    """
    工作模式：轮询 feed
    前端期望：{feed: [{contact_id, contact_name, messages: [{role, text}], ...}], newMessages:[], taskAcquisition:?}
    未配置微信解密或 DB 异常时仍返回 200 + 空 feed，避免顶部助手轮询刷 500。
    """
    per_contact = 10
    try:
        per_contact = int(request.args.get("per_contact", 10) or 10)
    except (TypeError, ValueError):
        per_contact = 10

    try:
        from app.utils.path_utils import get_resource_path as grp

        try:
            _ensure_decrypted_db()
        except Exception as sync_e:
            logger.debug("work_mode_feed: decrypt sync skipped: %s", sync_e)

        try:
            service = get_wechat_contact_service()
            contacts = service.get_contacts(contact_type="all", starred_only=True, limit=100) or []
        except Exception as svc_e:
            logger.warning("work_mode_feed: get_contacts failed: %s", svc_e)
            contacts = []

        feed = []
        for c in contacts:
            try:
                contact_id = c.get("id")
                contact_name = (
                    c.get("contact_name")
                    or c.get("remark")
                    or c.get("wechat_id")
                    or f"ID {contact_id}"
                )
                wechat_id = c.get("wechat_id")
                messages = []
                if wechat_id:
                    msg_db_path = os.path.join(
                        grp("wechat-decrypt"), "decrypted", "message", "message_0.db"
                    )
                    if os.path.exists(msg_db_path):
                        messages = _query_messages_from_hash_tables(
                            msg_db_path,
                            wechat_id,
                            limit=per_contact,
                            search_in_content=True,
                        )
                feed.append(
                    {
                        "contact_id": contact_id,
                        "contact_name": contact_name,
                        "messages": messages,
                    }
                )
            except Exception as row_e:
                logger.warning("work_mode_feed: skip one contact: %s", row_e)

        payload_ok = {
            "success": True,
            "feed": feed,
            "newMessages": [],
            "taskAcquisition": None,
            "per_contact": per_contact,
        }
        try:
            return jsonify(json_safe(payload_ok)), 200
        except Exception as json_e:
            logger.exception("work_mode_feed: jsonify failed: %s", json_e)
            # 仅含 JSON 原生类型，避免 json_safe 再失败
            return (
                jsonify(
                    {
                        "success": True,
                        "feed": [],
                        "newMessages": [],
                        "taskAcquisition": None,
                        "per_contact": per_contact,
                        "degraded": True,
                        "hint": (str(json_e) or "json")[:300],
                    }
                ),
                200,
            )
    except Exception as e:
        logger.exception("work_mode_feed: degraded empty response: %s", e)
        try:
            return (
                jsonify(
                    json_safe(
                        {
                            "success": True,
                            "feed": [],
                            "newMessages": [],
                            "taskAcquisition": None,
                            "per_contact": per_contact,
                            "degraded": True,
                            "hint": (str(e) or "error")[:300],
                        }
                    )
                ),
                200,
            )
        except Exception:
            return (
                jsonify(
                    {
                        "success": True,
                        "feed": [],
                        "newMessages": [],
                        "taskAcquisition": None,
                        "per_contact": per_contact,
                        "degraded": True,
                    }
                ),
                200,
            )


@wechat_contacts_bp.route("/send_message", methods=["POST"])
def send_message_by_name():
    """
    发送消息给微信联系人（按名称）
    """
    try:
        data = request.get_json() or {}
        contact_name = (data.get("contact_name") or "").strip()
        message = (data.get("message") or "").strip()
        if not contact_name:
            return jsonify({"success": False, "message": "联系人名称不能为空"}), 400
        if not message:
            return jsonify({"success": False, "message": "消息内容不能为空"}), 400

        from app.utils.path_utils import get_resource_path
        import sys
        sys_path = get_resource_path("wechat-decrypt")
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)

        from resources.wechat_cv.wechat_cv_send import search_and_send_by_cv
        result = search_and_send_by_cv(contact_name, message, delay=1.0, use_ocr=True)

        if result.get("status") == "success":
            return jsonify({
                "success": True,
                "message": f"已发送给 {contact_name}",
                "result": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": f"发送失败: {result.get('message', '未知错误')}",
                "result": result
            }), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"发送失败：{str(e)}"}), 500


@wechat_contacts_bp.route("/<int:contact_id>/send_message", methods=["POST"])
def send_message_to_contact(contact_id):
    """
    发送消息给微信联系人
    """
    try:
        data = request.get_json() or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"success": False, "message": "消息内容不能为空"}), 400

        service = get_wechat_contact_service()
        contact = service.get_contact_by_id(contact_id)
        if not contact:
            return jsonify({"success": False, "message": f"联系人不存在: {contact_id}"}), 404

        contact_name = contact.get("contact_name") or contact.get("remark") or contact.get("wechat_id") or f"ID {contact_id}"

        from app.utils.path_utils import get_resource_path
        import sys
        sys_path = get_resource_path("wechat-decrypt")
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)

        from resources.wechat_cv.wechat_cv_send import search_and_send_by_cv
        result = search_and_send_by_cv(contact_name, message, delay=1.0, use_ocr=True)

        if result.get("status") == "success":
            return jsonify({
                "success": True,
                "message": f"已发送给 {contact_name}",
                "result": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": f"发送失败: {result.get('message', '未知错误')}",
                "result": result
            }), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"发送失败：{str(e)}"}), 500
