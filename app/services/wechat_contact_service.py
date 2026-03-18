"""
微信联系人服务模块

提供微信联系人管理、业务逻辑处理。
"""

import os
import sys
import json
import logging
import threading
import time
import re
import difflib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import or_
from app.db.session import get_db
from app.db.models import WechatContact, WechatContactContext

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
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None
                    }
                    for c in contacts
                ]

        except Exception as e:
            logger.exception(f"获取联系人列表失败：{e}")
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
                project_root = os.path.dirname(base)
                wechat_decrypt_dir = os.path.join(project_root, "wechat-decrypt", "decrypted", "message")
                default_msg_db_path = os.path.join(wechat_decrypt_dir, "message_0.db")
                msg_db_path = os.environ.get("WECHAT_MSG_DB_PATH", default_msg_db_path)
                
                if not msg_db_path or not os.path.exists(msg_db_path):
                    logger.warning("微信消息数据库不存在：%s", msg_db_path)
                    return {
                        "success": False,
                        "message": "微信消息数据库不存在"
                    }
                
                try:
                    wechat_cv_path = os.path.join(project_root, "wechat_cv")
                    if os.path.isdir(wechat_cv_path) and wechat_cv_path not in sys.path:
                        sys.path.insert(0, wechat_cv_path)
                    from wechat_db_read import get_messages_for_contact, get_wechat_contact_db_path, get_contact_display_name
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
