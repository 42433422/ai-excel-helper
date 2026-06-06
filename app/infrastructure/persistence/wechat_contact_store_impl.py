from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from sqlalchemy import or_

from app.application.ports.wechat_contact_store import WechatContactStorePort
from app.db.models import WechatContact, WechatContactContext
from app.db.session import get_db
from app.utils.external_sqlite import sqlite_conn

logger = logging.getLogger(__name__)


def resolve_decrypt_contact_db_path() -> str | None:
    """
    解密后的微信 contact.db 路径（与搜索回退、同步共用）。
    优先 resources/wechat-decrypt，其次 AI助手 遗留目录，最后 WECHAT_CONTACT_DB_PATH。
    """
    from app.infrastructure.plugins.wechat_plugin import get_wechat_plugin
    from app.utils.path_utils import get_base_dir

    plugin = get_wechat_plugin()
    if plugin.is_available():
        p = plugin.get_decrypted_db_path("contact")
        if p and os.path.isfile(p):
            return p
    legacy = os.path.join(
        get_base_dir(),
        "AI助手",
        "wechat-decrypt",
        "decrypted",
        "contact",
        "contact.db",
    )
    if os.path.isfile(legacy):
        return legacy
    env = (os.environ.get("WECHAT_CONTACT_DB_PATH") or "").strip()
    if env and os.path.isfile(env):
        return env
    return None


def _read_rows_from_contact_db(path: str, limit: int) -> list[tuple[Any, ...]]:
    queries = [
        (
            "SELECT username, nick_name, remark, is_in_chat_room FROM contact "
            "WHERE IFNULL(delete_flag, 0) = 0 LIMIT ?"
        ),
        ("SELECT username, nick_name, remark, is_in_chat_room FROM contact " "LIMIT ?"),
    ]
    with sqlite_conn(path) as conn:
        for q in queries:
            try:
                cur = conn.execute(q, (limit,))
                return [tuple(r) for r in cur.fetchall()]
            except Exception:
                continue
    return []


class SQLAlchemyWechatContactStore(WechatContactStorePort):
    def list_contacts(
        self,
        *,
        keyword: str | None = None,
        contact_type: str | None = None,
        starred_only: bool = False,
        limit: int = 100,
        default_starred_when_all: bool = True,
    ) -> list[dict[str, Any]]:
        with get_db() as db:
            query = db.query(WechatContact).filter(WechatContact.is_active == 1)

            if keyword:
                pattern = f"%{keyword}%"
                query = query.filter(
                    or_(
                        WechatContact.contact_name.like(pattern),
                        WechatContact.remark.like(pattern),
                        WechatContact.wechat_id.like(pattern),
                    )
                )
            else:
                if contact_type == "all" and default_starred_when_all:
                    query = query.filter(WechatContact.is_starred == 1)
                elif contact_type and contact_type != "all":
                    query = query.filter(WechatContact.contact_type == contact_type)
                    # 星标联系人页：按「联系人/群聊」筛选时仍只显示已星标
                    if default_starred_when_all:
                        query = query.filter(WechatContact.is_starred == 1)

            if starred_only:
                query = query.filter(WechatContact.is_starred == 1)

            rows = query.order_by(WechatContact.contact_name).limit(limit).all()

            # 如果主表用 keyword 搜不到，则回退到 wechat-decrypt 的 contact.db
            if keyword and not rows:
                if starred_only:
                    return []

                try:
                    contact_db_path = resolve_decrypt_contact_db_path()
                    if not contact_db_path:
                        return []
                    if os.path.isfile(contact_db_path):
                        like = f"%{keyword}%"
                        sql = (
                            "SELECT username, nick_name, remark, is_in_chat_room "
                            "FROM contact "
                            "WHERE delete_flag = 0 AND (nick_name LIKE ? OR remark LIKE ? OR username LIKE ?) "
                            "LIMIT ?"
                        )

                        with sqlite_conn(contact_db_path) as cconn:
                            matches = cconn.execute(sql, (like, like, like, limit)).fetchall()

                        fallback: list[dict[str, Any]] = []
                        for username, nick_name, remark, is_in_chat_room in matches:
                            username = (username or "").strip()
                            nick_name = (nick_name or "").strip()
                            remark = (remark or "").strip()
                            ct = (
                                "group"
                                if (str(is_in_chat_room) == "1" or "@chatroom" in username)
                                else "contact"
                            )

                            if contact_type and contact_type != "all" and ct != contact_type:
                                continue

                            fallback.append(
                                {
                                    "id": None,
                                    "contact_name": nick_name or username,
                                    "remark": remark,
                                    "wechat_id": username,
                                    "contact_type": ct,
                                    "is_active": 1,
                                    "is_starred": 0,
                                    "created_at": None,
                                    "updated_at": None,
                                }
                            )

                        return fallback
                except Exception:
                    # 回退失败不影响主表流程
                    pass

            return [
                {
                    "id": c.id,
                    "contact_name": c.contact_name,
                    "remark": c.remark,
                    "wechat_id": c.wechat_id,
                    "contact_type": c.contact_type,
                    "is_active": c.is_active,
                    "is_starred": c.is_starred,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in rows
            ]

    def get_contact(self, contact_id: int) -> dict[str, Any] | None:
        with get_db() as db:
            c = (
                db.query(WechatContact)
                .filter(WechatContact.id == contact_id, WechatContact.is_active == 1)
                .first()
            )
            if not c:
                return None
            return {
                "id": c.id,
                "contact_name": c.contact_name,
                "remark": c.remark,
                "wechat_id": c.wechat_id,
                "contact_type": c.contact_type,
                "is_active": c.is_active,
                "is_starred": c.is_starred,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }

    def add_contact(
        self,
        *,
        contact_name: str,
        remark: str = "",
        wechat_id: str = "",
        contact_type: str = "contact",
        is_starred: bool = True,
    ) -> dict[str, Any]:
        name = (contact_name or "").strip()
        if not name:
            return {"success": False, "message": "联系人名称不能为空"}

        if contact_type not in ("contact", "group"):
            contact_type = "contact"

        wid = (wechat_id or "").strip()
        remark_s = (remark or "").strip()

        with get_db() as db:
            # 同步解密库后主库可能已有同 wechat_id 但未星标；应更新而非再 INSERT（避免重复行 / 唯一约束失败）
            if wid:
                existing = (
                    db.query(WechatContact)
                    .filter(WechatContact.wechat_id == wid, WechatContact.is_active == 1)
                    .first()
                )
                if existing:
                    existing.contact_name = name
                    existing.remark = remark_s
                    existing.contact_type = contact_type
                    existing.is_starred = 1 if is_starred else 0
                    existing.updated_at = datetime.now()
                    db.commit()
                    return {
                        "success": True,
                        "message": "已设为星标联系人" if is_starred else "已更新联系人",
                        "contact_id": existing.id,
                    }

            c = WechatContact(
                contact_name=name,
                remark=remark_s,
                wechat_id=wid,
                contact_type=contact_type,
                is_active=1,
                is_starred=1 if is_starred else 0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db.add(c)
            db.commit()
            db.refresh(c)
            return {"success": True, "message": "联系人添加成功", "contact_id": c.id}

    def update_contact(self, contact_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        with get_db() as db:
            c = (
                db.query(WechatContact)
                .filter(WechatContact.id == contact_id, WechatContact.is_active == 1)
                .first()
            )
            if not c:
                return {"success": False, "message": "联系人不存在"}

            if "contact_name" in fields and fields["contact_name"] is not None:
                name = str(fields["contact_name"]).strip()
                if not name:
                    return {"success": False, "message": "联系人名称不能为空"}
                c.contact_name = name
            if "remark" in fields and fields["remark"] is not None:
                c.remark = str(fields["remark"]).strip()
            if "wechat_id" in fields and fields["wechat_id"] is not None:
                c.wechat_id = str(fields["wechat_id"]).strip()
            if "contact_type" in fields and fields["contact_type"] is not None:
                ct = fields["contact_type"]
                if ct not in ("contact", "group"):
                    ct = "contact"
                c.contact_type = ct
            if "is_starred" in fields and fields["is_starred"] is not None:
                c.is_starred = 1 if bool(fields["is_starred"]) else 0

            c.updated_at = datetime.now()
            db.commit()
            return {"success": True, "message": "联系人更新成功"}

    def delete_contact(self, contact_id: int) -> dict[str, Any]:
        with get_db() as db:
            c = (
                db.query(WechatContact)
                .filter(WechatContact.id == contact_id, WechatContact.is_active == 1)
                .first()
            )
            if not c:
                return {"success": False, "message": "联系人不存在"}
            c.is_active = 0
            c.updated_at = datetime.now()
            db.commit()
            return {"success": True, "message": "联系人已删除"}

    def unstar_all(self) -> dict[str, Any]:
        with get_db() as db:
            count = (
                db.query(WechatContact)
                .filter(WechatContact.is_active == 1, WechatContact.is_starred == 1)
                .update({"is_starred": 0, "updated_at": datetime.now()})
            )
            db.commit()
            return {
                "success": True,
                "message": f"已取消全部星标，共 {count} 个联系人",
                "count": count,
            }

    def sync_from_decrypt_contact_db(self, limit: int = 50000) -> dict[str, Any]:
        """
        将解密库 contact.db 中的联系人导入主库 wechat_contacts（不自动星标）。
        导入后「搜索」可走主库；「星标列表」仍需用户手动添加星标。
        """
        path = resolve_decrypt_contact_db_path()
        if not path:
            return {
                "success": False,
                "imported": 0,
                "updated": 0,
                "skipped": 0,
                "message": (
                    "未找到解密联系人库 contact.db。"
                    "请将 wechat-decrypt 放到 resources/wechat-decrypt/"
                    "（需存在 decrypted/contact/contact.db），或设置环境变量 WECHAT_CONTACT_DB_PATH。"
                ),
            }
        rows = _read_rows_from_contact_db(path, limit)
        if not rows:
            return {
                "success": True,
                "imported": 0,
                "updated": 0,
                "skipped": 0,
                "message": (f"已连接解密库，但未读到联系人行（表为空或结构与预期不符）：{path}"),
                "source_path": path,
            }
        imported = 0
        updated = 0
        skipped = 0
        try:
            with get_db() as db:
                for row in rows:
                    if len(row) < 4:
                        skipped += 1
                        continue
                    username, nick_name, remark, is_in_chat_room = (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                    )
                    wid = (str(username) if username is not None else "").strip()
                    if not wid:
                        skipped += 1
                        continue
                    name = (str(nick_name) if nick_name is not None else "").strip() or wid
                    remark_s = (str(remark) if remark is not None else "").strip()
                    raw_room = str(is_in_chat_room or "")
                    ct = "group" if (raw_room == "1" or "@chatroom" in wid.lower()) else "contact"
                    c = db.query(WechatContact).filter(WechatContact.wechat_id == wid).first()
                    if c:
                        c.contact_name = name
                        c.remark = remark_s
                        c.contact_type = ct
                        c.is_active = 1
                        c.updated_at = datetime.now()
                        updated += 1
                    else:
                        db.add(
                            WechatContact(
                                contact_name=name,
                                remark=remark_s,
                                wechat_id=wid,
                                contact_type=ct,
                                is_active=1,
                                is_starred=0,
                                created_at=datetime.now(),
                                updated_at=datetime.now(),
                            )
                        )
                        imported += 1
                db.commit()
        except Exception as e:
            logger.exception("sync_from_decrypt_contact_db failed")
            return {
                "success": False,
                "imported": 0,
                "updated": 0,
                "skipped": 0,
                "message": str(e),
            }
        return {
            "success": True,
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "message": f"已从解密库同步：新增 {imported}，更新 {updated}（跳过 {skipped}）。",
            "source_path": path,
        }

    def get_context(self, contact_id: int) -> list[dict[str, Any]]:
        with get_db() as db:
            ctx = (
                db.query(WechatContactContext)
                .filter(WechatContactContext.contact_id == contact_id)
                .first()
            )
            if not ctx or not ctx.context_json:
                return []
            try:
                return json.loads(ctx.context_json)
            except Exception:
                return []

    def save_context(self, contact_id: int, wechat_id: str, messages: list[dict[str, Any]]) -> bool:
        with get_db() as db:
            ctx = (
                db.query(WechatContactContext)
                .filter(WechatContactContext.contact_id == contact_id)
                .first()
            )
            if ctx:
                ctx.wechat_id = wechat_id
                ctx.context_json = json.dumps(messages, ensure_ascii=False)
                ctx.message_count = len(messages)
                ctx.updated_at = datetime.now()
            else:
                ctx = WechatContactContext(
                    contact_id=contact_id,
                    wechat_id=wechat_id,
                    context_json=json.dumps(messages, ensure_ascii=False),
                    message_count=len(messages),
                    updated_at=datetime.now(),
                )
                db.add(ctx)
            db.commit()
            return True
