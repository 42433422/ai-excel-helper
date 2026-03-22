"""
微信联系人服务模块

提供微信联系人管理、业务逻辑处理。
"""

import difflib
import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_

from app.db.models import WechatContact, WechatContactContext
from app.db.session import get_db

logger = logging.getLogger(__name__)


class WechatContactService:
    """微信联系人服务类"""

    def __init__(self):
        pass

    def get_contacts(
        self,
        keyword: Optional[str] = None,
        contact_type: Optional[str] = None,
        starred_only: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取微信联系人列表

        Args:
            keyword: 搜索关键词
            contact_type: 联系人类型 (contact/group/all)
            starred_only: 只返回星标联系人
            limit: 返回数量限制
        """
        try:
            with get_db() as db:
                query = db.query(WechatContact).filter(WechatContact.is_active == 1)
                
                # 优先处理搜索关键词
                if keyword:
                    pattern = f"%{keyword}%"
                    query = query.filter(
                        or_(
                            WechatContact.contact_name.like(pattern),
                            WechatContact.remark.like(pattern),
                            WechatContact.wechat_id.like(pattern)
                        )
                    )
                # 处理类型筛选
                elif contact_type == "all":
                    # 当类型为"全部"且没有搜索关键词时，默认只显示星标联系人
                    query = query.filter(WechatContact.is_starred == 1)
                elif contact_type and contact_type != "all":
                    query = query.filter(WechatContact.contact_type == contact_type)
                
                # 处理星标筛选
                if starred_only:
                    query = query.filter(WechatContact.is_starred == 1)
                
                query = query.order_by(WechatContact.contact_name).limit(limit)
                contacts = query.all()

                results = [
                    {
                        "id": c.id,
                        "contact_name": c.contact_name,
                        "remark": c.remark,
                        "wechat_id": c.wechat_id,
                        "contact_type": c.contact_type,
                        "is_active": c.is_active,
                        "is_starred": c.is_starred,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None
                    }
                    for c in contacts
                ]

                # 如果带关键词且本地表没有结果，回退到微信数据库中“挖”联系人（类似旧 AI 助手逻辑）
                if keyword and not results:
                    try:
                        extra = self._search_contacts_from_wechat_db(keyword=keyword, limit=limit)
                        results.extend(extra)
                    except Exception as e:
                        logger.warning("从微信数据库搜索联系人失败：%s", e)

                return results

        except Exception as e:
            logger.exception(f"获取联系人列表失败：{e}")
            return []

    def _search_contacts_from_wechat_db(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        从微信解密数据库中搜索联系人（仅用于补充搜索结果，不写入主表）。

        - 数据来源：resources/wechat-decrypt/decrypted/message/message_0.db
        - 工具模块：wechat_db_read.get_recent_messages（来自 resources/wechat_cv）
        """
        keyword = (keyword or "").strip()
        if not keyword:
            return []

        try:
            import os
            import sqlite3
            import sys

            from app.utils.path_utils import get_base_dir, get_resource_path

            # 1) 优先使用 XCAGI/resources 下的解密库
            wechat_decrypt_dir = get_resource_path("wechat-decrypt", "decrypted", "message")
            candidate_db_paths = [os.path.join(wechat_decrypt_dir, "message_0.db")]

            # 2) 兼容：使用 XCAGI/AI助手 下原有的解密库位置（如果存在）
            base_dir = get_base_dir()
            legacy_ai_dir = os.path.join(base_dir, "AI助手")
            candidate_db_paths.append(os.path.join(legacy_ai_dir, "wechat-decrypt", "decrypted", "message", "message_0.db"))

            msg_db_path = os.environ.get("WECHAT_MSG_DB_PATH", "")
            if msg_db_path and os.path.exists(msg_db_path):
                db_path = msg_db_path
            else:
                db_path = next((p for p in candidate_db_paths if os.path.exists(p)), "")

            if not db_path:
                return []

            # 先尝试从 contact.db 直接匹配联系人（通常“昵称/备注/微信号”都在这里）
            try:
                wechat_decrypt_base = os.path.dirname(wechat_decrypt_dir)  # .../decrypted
                contact_db_path = os.path.join(wechat_decrypt_base, "contact", "contact.db")
                logger.info("[contact-fallback] path=%s exists=%s keyword=%s", contact_db_path, os.path.exists(contact_db_path), keyword)
                if os.path.exists(contact_db_path):
                    with sqlite3.connect(contact_db_path) as cconn:
                        cur = cconn.cursor()
                        like = f"%{keyword}%"
                        sql = (
                            "SELECT username, nick_name, remark, is_in_chat_room "
                            "FROM contact "
                            "WHERE delete_flag = 0 AND (nick_name LIKE ? OR remark LIKE ? OR username LIKE ?) "
                            "LIMIT ?"
                        )
                        rows = cur.execute(sql, (like, like, like, limit)).fetchall()
                        logger.info("contact.db matched rows=%s for keyword=%s", len(rows), keyword)
                        contacts = []
                        for username, nick_name, remark, is_in_chat_room in rows:
                            username = (username or "").strip()
                            nick_name = (nick_name or "").strip()
                            remark = (remark or "").strip()
                            contact_type = "group" if (str(is_in_chat_room) == "1" or "@chatroom" in username) else "contact"
                            contacts.append(
                                {
                                    "id": None,
                                    "contact_name": nick_name or username,
                                    "remark": remark,
                                    "wechat_id": username,
                                    "contact_type": contact_type,
                                    "is_active": 1,
                                    "is_starred": 0,
                                    "created_at": None,
                                    "updated_at": None,
                                }
                            )
                        if contacts:
                            return contacts
            except Exception as e:
                # contact.db 不可用时继续走 message db 回退
                logger.warning("contact.db 搜索联系人失败：%s", e)

            # 3) wechat_db_read 所在目录：先看 resources/wechat_cv，再回退 AI助手/wechat_cv
            wechat_cv_candidates = [
                get_resource_path("wechat_cv"),
                os.path.join(legacy_ai_dir, "wechat_cv"),
            ]
            wechat_cv_path = next((p for p in wechat_cv_candidates if os.path.isdir(p)), "")
            if wechat_cv_path and wechat_cv_path not in sys.path:
                sys.path.insert(0, wechat_cv_path)

            try:
                from wechat_db_read import get_recent_messages  # type: ignore
            except Exception as e:
                logger.warning("导入 wechat_db_read 失败，无法从微信 DB 搜索联系人：%s", e)
                return []

            # 这份 message_0.db 可能是不同版本/不同导出方式，表名常见有两类：
            # - 旧版：MSG/Message，字段有 talker/displayName
            # - 新版：Msg_<hash>，字段多为 message_content 等
            # 为了稳定，这里先用 sqlite3 直接拉取“最可能的消息表”，再做兼容解析。
            rows: List[Dict[str, Any]] = []
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                tbls = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [t[0] for t in tbls if t and t[0]]
                msg_table = (
                    "MSG"
                    if "MSG" in table_names
                    else ("Message" if "Message" in table_names else next((t for t in table_names if str(t).startswith("Msg_")), ""))
                )
                if msg_table:
                    raw = cur.execute(f"SELECT * FROM {msg_table} LIMIT ?", (limit * 5,)).fetchall()
                    colnames = [d[0] for d in (cur.description or [])]
                    rows = [dict(zip(colnames, r)) for r in raw]
                conn.close()
            except Exception:
                # 退化：走原本 wechat_db_read 的逻辑（可能会失败，但不影响主流程）
                out = get_recent_messages(
                    db_path,
                    limit=limit * 5,  # 多取一些，再按联系人去重
                    table_name="MSG",
                    config_path=os.environ.get("WECHAT_DB_KEY_CONFIG") or None,
                )
                rows = out.get("rows") or []

            if not rows:
                return []

            keyword_lower = keyword.lower()
            contacts_map: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                username = (row.get("talker") or "").strip()
                display_name = (row.get("displayName") or "").strip()
                if username or display_name:
                    # 旧版字段路径
                    text = f"{username} {display_name}".lower()
                    if keyword_lower not in text:
                        continue

                    key = username or display_name
                    if key in contacts_map:
                        continue

                    contacts_map[key] = {
                        "id": None,
                        "contact_name": display_name or username,
                        "remark": "",
                        "wechat_id": username or "",
                        "contact_type": "group" if "@chatroom" in (username or "") else "contact",
                        "is_active": 1,
                        "is_starred": 0,
                        "created_at": None,
                        "updated_at": None,
                    }
                else:
                    # 新版字段路径：从 message_content 里抽取 wxid_xxx: 作为“对方标识”
                    mc = row.get("message_content") or ""
                    if isinstance(mc, (bytes, bytearray)):
                        mc = mc.decode("utf-8", errors="ignore")
                    mc_str = str(mc)
                    if keyword_lower not in mc_str.lower():
                        continue

                    m = re.search(r"(wxid_[0-9a-zA-Z]+)\\s*:", mc_str)
                    wechat_id = m.group(1) if m else ""
                    if not wechat_id:
                        continue

                    if wechat_id in contacts_map:
                        continue

                    contacts_map[wechat_id] = {
                        "id": None,
                        "contact_name": wechat_id,
                        "remark": "",
                        "wechat_id": wechat_id,
                        "contact_type": "contact",
                        "is_active": 1,
                        "is_starred": 0,
                        "created_at": None,
                        "updated_at": None,
                    }

                if len(contacts_map) >= limit:
                    break

            return list(contacts_map.values())
        except Exception as e:
            logger.exception("从微信 DB 搜索联系人时异常：%s", e)
            return []

    def get_contact_by_id(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取联系人"""
        try:
            with get_db() as db:
                contact = db.query(WechatContact).filter(
                    WechatContact.id == contact_id,
                    WechatContact.is_active == 1
                ).first()

                if not contact:
                    return None

                return {
                    "id": contact.id,
                    "contact_name": contact.contact_name,
                    "remark": contact.remark,
                    "wechat_id": contact.wechat_id,
                    "contact_type": contact.contact_type,
                    "is_active": contact.is_active,
                    "is_starred": contact.is_starred,
                    "created_at": contact.created_at.isoformat() if contact.created_at else None,
                    "updated_at": contact.updated_at.isoformat() if contact.updated_at else None
                }

        except Exception as e:
            logger.error(f"获取联系人失败：{e}")
            return None

    def add_contact(
        self,
        contact_name: str,
        remark: Optional[str] = None,
        wechat_id: Optional[str] = None,
        contact_type: str = "contact",
        is_starred: bool = True
    ) -> Dict[str, Any]:
        """
        添加微信联系人

        Args:
            contact_name: 联系人名称
            remark: 备注
            wechat_id: 微信号
            contact_type: 联系人类型
            is_starred: 是否星标

        Returns:
            结果字典
        """
        try:
            contact_name = (contact_name or "").strip()
            if not contact_name:
                return {"success": False, "message": "联系人名称不能为空"}

            if contact_name in ("%", "%s") or (len(contact_name) <= 3 and contact_name.startswith("%")):
                contact_name = wechat_id or "未知"

            with get_db() as db:
                contact = WechatContact(
                    contact_name=contact_name,
                    remark=remark or "",
                    wechat_id=wechat_id or "",
                    contact_type=contact_type,
                    is_active=1,
                    is_starred=1 if is_starred else 0
                )
                db.add(contact)
                db.commit()
                db.refresh(contact)

                return {
                    "success": True,
                    "message": "联系人添加成功",
                    "contact_id": contact.id
                }

        except Exception as e:
            logger.exception(f"添加联系人失败：{e}")
            return {"success": False, "message": str(e)}

    def update_contact(
        self,
        contact_id: int,
        contact_name: Optional[str] = None,
        remark: Optional[str] = None,
        wechat_id: Optional[str] = None,
        contact_type: Optional[str] = None,
        is_starred: Optional[bool] = None
    ) -> Dict[str, Any]:
        """更新联系人"""
        try:
            with get_db() as db:
                contact = db.query(WechatContact).filter(
                    WechatContact.id == contact_id,
                    WechatContact.is_active == 1
                ).first()

                if not contact:
                    return {"success": False, "message": "联系人不存在"}

                if contact_name is not None:
                    if not contact_name.strip():
                        return {"success": False, "message": "联系人名称不能为空"}
                    contact.contact_name = contact_name.strip()

                if remark is not None:
                    contact.remark = remark.strip()

                if wechat_id is not None:
                    contact.wechat_id = wechat_id.strip()

                if contact_type is not None:
                    if contact_type not in ("contact", "group"):
                        contact_type = "contact"
                    contact.contact_type = contact_type

                if is_starred is not None:
                    contact.is_starred = 1 if is_starred else 0

                contact.updated_at = datetime.now()
                db.commit()

                return {"success": True, "message": "联系人更新成功"}

        except Exception as e:
            logger.exception(f"更新联系人失败：{e}")
            return {"success": False, "message": str(e)}

    def delete_contact(self, contact_id: int) -> Dict[str, Any]:
        """删除联系人（软删除）"""
        try:
            with get_db() as db:
                contact = db.query(WechatContact).filter(
                    WechatContact.id == contact_id,
                    WechatContact.is_active == 1
                ).first()

                if not contact:
                    return {"success": False, "message": "联系人不存在"}

                contact.is_active = 0
                contact.updated_at = datetime.now()
                db.commit()

                return {"success": True, "message": "联系人已删除"}

        except Exception as e:
            logger.exception(f"删除联系人失败：{e}")
            return {"success": False, "message": str(e)}

    def star_contact(self, contact_id: int, starred: bool = True) -> Dict[str, Any]:
        """设置联系人星标状态"""
        return self.update_contact(contact_id, is_starred=starred)

    def unstar_all(self) -> Dict[str, Any]:
        """取消所有联系人星标"""
        try:
            with get_db() as db:
                count = db.query(WechatContact).filter(
                    WechatContact.is_active == 1,
                    WechatContact.is_starred == 1
                ).update({
                    "is_starred": 0,
                    "updated_at": datetime.now()
                })
                db.commit()

                return {
                    "success": True,
                    "message": f"已取消全部星标，共 {count} 个联系人",
                    "count": count
                }

        except Exception as e:
            logger.exception(f"取消星标失败：{e}")
            return {"success": False, "message": str(e)}

    def get_contact_context(self, contact_id: int) -> List[Dict[str, Any]]:
        """获取联系人聊天上下文"""
        try:
            with get_db() as db:
                context = db.query(WechatContactContext).filter(
                    WechatContactContext.contact_id == contact_id
                ).first()

                if not context or not context.context_json:
                    return []

                try:
                    return json.loads(context.context_json)
                except Exception:
                    return []

        except Exception as e:
            logger.error(f"获取联系人上下文失败：{e}")
            return []

    def save_contact_context(
        self,
        contact_id: int,
        wechat_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """保存联系人聊天上下文"""
        try:
            with get_db() as db:
                context = db.query(WechatContactContext).filter(
                    WechatContactContext.contact_id == contact_id
                ).first()

                if context:
                    context.wechat_id = wechat_id
                    context.context_json = json.dumps(messages, ensure_ascii=False)
                    context.message_count = len(messages)
                    context.updated_at = datetime.now()
                else:
                    context = WechatContactContext(
                        contact_id=contact_id,
                        wechat_id=wechat_id,
                        context_json=json.dumps(messages, ensure_ascii=False),
                        message_count=len(messages)
                    )
                    db.add(context)

                db.commit()
                return True

        except Exception as e:
            logger.exception(f"保存联系人上下文失败：{e}")
            return False

    def resolve_send_message(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """
        从消息中解析出发送目标和内容

        Args:
            message: 用户消息，如 "给张三发送内容"

        Returns:
            (contact_name, content) 或 (None, None)
        """
        message = (message or "").strip()
        if not message or len(message) < 4:
            return None, None

        patterns = [
            r"^给\s*([^：:\s]+(?:\s+[^：:\s]+)*?)\s*(?:发送|发)\s*[：:\s]?\s*(.+)$",
            r"^(?:发送消息给|发消息给|发给|发送给)\s*([^：:\s]+(?:\s+[^：:\s]+)*?)\s*[：:\s]\s*(.+)$",
            r"^(?:发送消息给|发消息给|发给|发送给)(.+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    contact_part = groups[0].strip()
                    content = groups[1].strip()
                else:
                    contact_part = groups[0].strip()
                    content = None

                if not contact_part:
                    continue

                contact = self._find_best_matching_contact(contact_part)
                if contact and content:
                    return contact, content

        return None, None

    def _find_best_matching_contact(self, contact_part: str) -> Optional[str]:
        """模糊匹配联系人"""
        contacts = self.get_contacts(keyword=contact_part, starred_only=False, limit=10)

        if not contacts:
            return None

        target = re.sub(r"\s+", "", contact_part.lower())

        best_name = None
        best_score = 0.0

        for c in contacts:
            name = (c.get("contact_name") or "").strip()
            if not name:
                continue

            norm = re.sub(r"\s+", "", name.lower())
            score = difflib.SequenceMatcher(None, target, norm).ratio()

            if score > best_score and score >= 0.5:
                best_score = score
                best_name = name

        return best_name

    def refresh_messages(self, contact_id: int, limit: int = 50) -> Dict[str, Any]:
        """
        从微信数据库拉取最新消息并保存到聊天上下文
        
        Args:
            contact_id: 联系人 ID
            limit: 拉取消息数量限制，默认 50
            
        Returns:
            结果字典，包含 success, message, count 等信息
        """
        try:
            import os
            import sys
            
            with get_db() as db:
                contact = db.query(WechatContact).filter(
                    WechatContact.id == contact_id,
                    WechatContact.is_active == 1
                ).first()
                
                if not contact:
                    return {
                        "success": False,
                        "message": "联系人不存在"
                    }
                
                wechat_id = contact.wechat_id or contact.contact_name
                if not wechat_id:
                    return {
                        "success": False,
                        "message": "联系人微信号或名称为空"
                    }
                
                base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                from app.utils.path_utils import get_resource_path

                wechat_decrypt_dir = get_resource_path("wechat-decrypt", "decrypted", "message")
                default_msg_db_path = os.path.join(wechat_decrypt_dir, "message_0.db")
                msg_db_path = os.environ.get("WECHAT_MSG_DB_PATH", default_msg_db_path)
                
                if not msg_db_path or not os.path.exists(msg_db_path):
                    logger.warning("微信消息数据库不存在：%s", msg_db_path)
                    return {
                        "success": False,
                        "message": "微信消息数据库不存在"
                    }
                
                try:
                    wechat_cv_path = get_resource_path("wechat_cv")
                    if os.path.isdir(wechat_cv_path) and wechat_cv_path not in sys.path:
                        sys.path.insert(0, wechat_cv_path)
                    from wechat_db_read import (
                        get_contact_display_name,
                        get_messages_for_contact,
                        get_wechat_contact_db_path,
                    )
                except Exception as e:
                    logger.warning("导入 wechat_db_read 失败：%s", e)
                    return {
                        "success": False,
                        "message": f"导入微信数据库模块失败：{str(e)}"
                    }
                
                contact_db_path = get_wechat_contact_db_path()
                
                messages_result = get_messages_for_contact(
                    msg_db_path=msg_db_path,
                    talker=wechat_id,
                    limit=limit,
                    only_other=False,
                    config_path=os.environ.get("WECHAT_DB_KEY_CONFIG")
                )
                
                if not messages_result.get("success"):
                    return {
                        "success": False,
                        "message": f"读取微信消息失败：{messages_result.get('message', '未知错误')}"
                    }
                
                rows = messages_result.get("rows", [])
                if not rows:
                    return {
                        "success": True,
                        "message": "未找到新消息",
                        "count": 0
                    }
                
                messages = []
                for row in rows:
                    role = row.get("role", "other")
                    text = row.get("text", "")
                    if text:
                        messages.append({
                            "role": role,
                            "text": text
                        })
                
                self.save_contact_context(
                    contact_id=contact_id,
                    wechat_id=wechat_id,
                    messages=messages
                )
                
                logger.info(f"刷新联系人消息成功 contact_id={contact_id}, count={len(messages)}")
                
                return {
                    "success": True,
                    "message": f"成功拉取 {len(messages)} 条消息",
                    "count": len(messages)
                }
                
        except Exception as e:
            logger.exception(f"刷新联系人消息失败：{e}")
            return {
                "success": False,
                "message": f"刷新失败：{str(e)}"
            }


wechat_contact_service = WechatContactService()


def get_wechat_contact_service() -> WechatContactService:
    return wechat_contact_service
