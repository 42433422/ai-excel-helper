from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from app.application.ports.wechat_contact_store import WechatContactStorePort
from app.db.models import WechatContact, WechatContactContext
from app.db.session import get_db
from app.utils.external_sqlite import sqlite_conn


class SQLAlchemyWechatContactStore(WechatContactStorePort):
    def list_contacts(
        self,
        *,
        keyword: Optional[str] = None,
        contact_type: Optional[str] = None,
        starred_only: bool = False,
        limit: int = 100,
        default_starred_when_all: bool = True,
    ) -> List[Dict[str, Any]]:
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

            if starred_only:
                query = query.filter(WechatContact.is_starred == 1)

            rows = query.order_by(WechatContact.contact_name).limit(limit).all()

            # 如果主表用 keyword 搜不到，则回退到 wechat-decrypt 的 contact.db
            if keyword and not rows:
                if starred_only:
                    return []

                try:
                    from app.infrastructure.plugins.wechat_plugin import get_wechat_plugin

                    plugin = get_wechat_plugin()
                    contact_db_path = plugin.get_decrypted_db_path("contact")
                    if not contact_db_path:
                        return []
                    if contact_db_path and os.path.exists(contact_db_path):
                        like = f"%{keyword}%"
                        sql = (
                            "SELECT username, nick_name, remark, is_in_chat_room "
                            "FROM contact "
                            "WHERE delete_flag = 0 AND (nick_name LIKE ? OR remark LIKE ? OR username LIKE ?) "
                            "LIMIT ?"
                        )

                        with sqlite_conn(contact_db_path) as cconn:
                            matches = cconn.execute(sql, (like, like, like, limit)).fetchall()

                        fallback: List[Dict[str, Any]] = []
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

    def get_contact(self, contact_id: int) -> Optional[Dict[str, Any]]:
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
    ) -> Dict[str, Any]:
        name = (contact_name or "").strip()
        if not name:
            return {"success": False, "message": "联系人名称不能为空"}

        if contact_type not in ("contact", "group"):
            contact_type = "contact"

        with get_db() as db:
            c = WechatContact(
                contact_name=name,
                remark=(remark or "").strip(),
                wechat_id=(wechat_id or "").strip(),
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

    def update_contact(self, contact_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
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

    def delete_contact(self, contact_id: int) -> Dict[str, Any]:
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

    def unstar_all(self) -> Dict[str, Any]:
        with get_db() as db:
            count = (
                db.query(WechatContact)
                .filter(WechatContact.is_active == 1, WechatContact.is_starred == 1)
                .update({"is_starred": 0, "updated_at": datetime.now()})
            )
            db.commit()
            return {"success": True, "message": f"已取消全部星标，共 {count} 个联系人", "count": count}

    def get_context(self, contact_id: int) -> List[Dict[str, Any]]:
        with get_db() as db:
            ctx = db.query(WechatContactContext).filter(WechatContactContext.contact_id == contact_id).first()
            if not ctx or not ctx.context_json:
                return []
            try:
                return json.loads(ctx.context_json)
            except Exception:
                return []

    def save_context(self, contact_id: int, wechat_id: str, messages: List[Dict[str, Any]]) -> bool:
        with get_db() as db:
            ctx = db.query(WechatContactContext).filter(WechatContactContext.contact_id == contact_id).first()
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

