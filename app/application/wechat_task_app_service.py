"""
微信任务应用服务

此模块已迁移到 app/application/
"""

import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.db.models import WechatTask
from app.db.session import get_db

logger = logging.getLogger(__name__)


class WechatTaskApplicationService:
    """微信任务应用服务"""

    def __init__(self):
        pass

    def _insert_or_ignore_wechat_task(
        self,
        *,
        contact_id: Optional[int] = None,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        message_id: Optional[str] = None,
        msg_timestamp: Optional[int] = None,
        raw_text: str,
        task_type: str = "unknown",
    ) -> Optional[int]:
        if not raw_text:
            return None

        try:
            with get_db() as db:
                if message_id and username:
                    existing = db.query(WechatTask).filter(
                        WechatTask.message_id == message_id,
                        WechatTask.username == username
                    ).first()
                    if existing:
                        return existing.id

                task = WechatTask(
                    contact_id=contact_id,
                    username=username,
                    display_name=display_name,
                    message_id=message_id,
                    msg_timestamp=msg_timestamp,
                    raw_text=raw_text,
                    task_type=task_type,
                    status="pending"
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                return task.id
        except IntegrityError:
            with get_db() as db:
                if message_id and username:
                    existing = db.query(WechatTask).filter(
                        WechatTask.message_id == message_id,
                        WechatTask.username == username
                    ).first()
                    if existing:
                        return existing.id
            return None
        except Exception as e:
            logger.error(f"插入 wechat_task 失败：{e}")
            return None

    def scan_messages(
        self,
        contact_id: Optional[int] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        try:
            logger.info("开始扫描微信消息，contact_id=%s, limit=%s", contact_id, limit)

            from app.utils.path_utils import get_resource_path

            wechat_decrypt_dir = get_resource_path("wechat-decrypt", "decrypted", "message")
            default_msg_db_path = os.path.join(wechat_decrypt_dir, "message_0.db")
            msg_db_path = os.environ.get("WECHAT_MSG_DB_PATH", default_msg_db_path)

            if not msg_db_path or not os.path.exists(msg_db_path):
                logger.warning("微信消息数据库不存在：%s", msg_db_path)
                return []

            try:
                wechat_cv_path = get_resource_path("wechat_cv")
                if os.path.isdir(wechat_cv_path) and wechat_cv_path not in sys.path:
                    sys.path.insert(0, wechat_cv_path)
                from wechat_db_read import get_recent_messages
            except Exception as e:
                logger.warning("导入 wechat_db_read 失败，无法扫描微信消息：%s", e)
                return []

            out = get_recent_messages(
                msg_db_path,
                limit=limit,
                table_name="MSG",
                config_path=os.environ.get("WECHAT_DB_KEY_CONFIG") or None,
            )
            rows = out.get("rows") or []
            if not rows:
                return []

            new_tasks: List[Dict[str, Any]] = []
            for row in rows:
                message_id = str(row.get("msgId") or row.get("localId") or "")
                username = row.get("talker") or ""
                display_name = row.get("displayName") or ""
                msg_timestamp = int(row.get("createTime") or 0)
                raw_text = (row.get("content") or "").strip()
                if not raw_text:
                    continue

                if not self._is_order_like_message(raw_text):
                    continue

                task_type = self._infer_task_type_from_text(raw_text)

                task_id = self._insert_or_ignore_wechat_task(
                    contact_id=contact_id,
                    username=username,
                    display_name=display_name,
                    message_id=message_id or None,
                    msg_timestamp=msg_timestamp,
                    raw_text=raw_text,
                    task_type=task_type,
                )
                if task_id:
                    new_tasks.append({
                        "id": task_id,
                        "username": username,
                        "display_name": display_name,
                        "message_id": message_id,
                        "msg_timestamp": msg_timestamp,
                        "raw_text": raw_text,
                        "task_type": task_type,
                    })

            logger.info("微信消息扫描完成，新任务数量：%d", len(new_tasks))
            return new_tasks

        except Exception as e:
            logger.exception("扫描微信消息失败：%s", e)
            return []

    def _is_order_like_message(self, text: str) -> bool:
        if not text or len(text) < 4:
            return False
        msg = text.strip()
        if any(k in msg for k in ("查询", "查看", "哪些", "列表")):
            return False
        if "规格" not in msg:
            return False
        if not re.search(r"(桶|公斤|kg)", msg, re.I):
            return False
        return True

    def _infer_task_type_from_text(self, text: str) -> str:
        if self._is_order_like_message(text):
            return "shipment_order"
        return "unknown"

    def process_message(self, task_id: int) -> Dict[str, Any]:
        try:
            task = self._get_task(task_id)
            if not task:
                return {"success": False, "message": "任务不存在"}

            message_type = self._recognize_message_type(task.get("raw_text", ""))

            if message_type == "order":
                result = self._process_order_message(task)
            elif message_type == "shipment":
                result = self._process_shipment_message(task)
            else:
                result = {"success": True, "message": "消息类型未知，已标记为待处理"}

            if result.get("success"):
                self._update_task_status(task_id, "done")
            else:
                self._update_task_status(task_id, "pending")

            return result

        except Exception as e:
            logger.exception(f"处理微信消息失败：{e}")
            return {"success": False, "message": f"处理失败：{str(e)}"}

    def recognize_order(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            patterns = [
                r'(?:买|要|需要|订购|下单)\s*(\d+)\s*(箱|件|个|盒|桶)\s*(.+)',
                r'(\d+)\s*(箱|件|个|盒|桶)\s*(.+)',
                r'(.+?)\s*(\d+)\s*(箱|件|个|盒|桶)',
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if pattern.startswith(r'(?:'):
                        quantity = int(match.group(1))
                        unit = match.group(2)
                        product = match.group(3)
                    elif pattern.endswith(r'(.+)'):
                        quantity = int(match.group(1))
                        unit = match.group(2)
                        product = match.group(3)
                    else:
                        product = match.group(1)
                        quantity = int(match.group(2))
                        unit = match.group(3)

                    return {
                        "type": "order",
                        "quantity": quantity,
                        "unit": unit,
                        "product": product.strip(),
                        "raw_text": text
                    }

            return None

        except Exception as e:
            logger.error(f"识别订单失败：{e}")
            return None

    def recognize_shipment(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            patterns = [
                r'发货[：:]\s*(.+)',
                r'已发货\s*(.+)',
                r'发出\s*(.+)',
                r'安排发货[：:]\s*(.+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    content = match.group(1).strip()
                    order_info = self.recognize_order(content)

                    return {
                        "type": "shipment",
                        "content": content,
                        "products": order_info if order_info else None,
                        "raw_text": text
                    }

            return None

        except Exception as e:
            logger.error(f"识别发货单失败：{e}")
            return None

    def confirm_task(self, task_id: int) -> Dict[str, Any]:
        try:
            if not self._task_exists(task_id):
                return {"success": False, "message": "任务不存在"}

            self._update_task_status(task_id, "confirmed")

            return {"success": True, "message": "任务已确认"}

        except Exception as e:
            logger.exception(f"确认任务失败：{e}")
            return {"success": False, "message": f"确认失败：{str(e)}"}

    def ignore_task(self, task_id: int) -> Dict[str, Any]:
        try:
            if not self._task_exists(task_id):
                return {"success": False, "message": "任务不存在"}

            self._update_task_status(task_id, "ignored")

            return {"success": True, "message": "任务已忽略"}

        except Exception as e:
            logger.exception(f"忽略任务失败：{e}")
            return {"success": False, "message": f"忽略失败：{str(e)}"}

    def get_tasks(
        self,
        contact_id: Optional[int] = None,
        status: str = "pending",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        try:
            logger.info(f"查询任务列表，contact_id={contact_id}, status={status}")

            with get_db() as db:
                query = db.query(WechatTask).filter(WechatTask.status == status)

                if contact_id is not None:
                    query = query.filter(WechatTask.contact_id == contact_id)

                query = query.order_by(WechatTask.msg_timestamp.desc(), WechatTask.id.desc()).limit(limit)
                tasks = query.all()

                return [
                    {
                        "id": t.id,
                        "contact_id": t.contact_id,
                        "username": t.username,
                        "display_name": t.display_name,
                        "message_id": t.message_id,
                        "msg_timestamp": t.msg_timestamp,
                        "raw_text": t.raw_text,
                        "task_type": t.task_type,
                        "status": t.status,
                        "last_status_at": t.last_status_at.isoformat() if t.last_status_at else None,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "updated_at": t.updated_at.isoformat() if t.updated_at else None
                    }
                    for t in tasks
                ]

        except Exception as e:
            logger.exception(f"查询任务列表失败：{e}")
            return []

    def get_contacts(
        self,
        keyword: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            logger.info(f"查询联系人列表，keyword={keyword}, limit={limit}")

            with get_db() as db:
                query = db.query(
                    WechatTask.username,
                    WechatTask.display_name,
                    WechatTask.contact_id,
                    func.max(WechatTask.msg_timestamp).label("last_message_time"),
                    func.count(WechatTask.id).label("message_count")
                )

                if keyword:
                    pattern = f"%{keyword}%"
                    query = query.filter(
                        or_(
                            WechatTask.username.like(pattern),
                            WechatTask.display_name.like(pattern)
                        )
                    )

                query = query.group_by(
                    WechatTask.username,
                    WechatTask.display_name,
                    WechatTask.contact_id
                ).order_by(
                    func.max(WechatTask.msg_timestamp).desc()
                ).limit(limit)

                results = query.all()

                contacts = []
                for row in results:
                    contacts.append({
                        "username": row.username or "",
                        "display_name": row.display_name or "",
                        "contact_id": row.contact_id,
                        "last_message_time": row.last_message_time,
                        "message_count": row.message_count or 0
                    })

            logger.info(f"查询到 {len(contacts)} 个联系人")
            return contacts

        except Exception as e:
            logger.exception(f"查询联系人列表失败：{e}")
            return []

    def _get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                task = db.query(WechatTask).filter(WechatTask.id == task_id).first()
                if task:
                    return {
                        "id": task.id,
                        "contact_id": task.contact_id,
                        "username": task.username,
                        "display_name": task.display_name,
                        "message_id": task.message_id,
                        "msg_timestamp": task.msg_timestamp,
                        "raw_text": task.raw_text,
                        "task_type": task.task_type,
                        "status": task.status,
                        "last_status_at": task.last_status_at,
                        "created_at": task.created_at,
                        "updated_at": task.updated_at
                    }
                return None
        except Exception as e:
            logger.error(f"获取任务失败：{e}")
            return None

    def _task_exists(self, task_id: int) -> bool:
        try:
            with get_db() as db:
                exists = db.query(WechatTask.id).filter(WechatTask.id == task_id).first() is not None
                return exists
        except Exception as e:
            logger.error(f"检查任务存在失败：{e}")
            return False

    def _update_task_status(self, task_id: int, status: str) -> bool:
        try:
            if status not in ("pending", "confirmed", "done", "ignored"):
                raise ValueError(f"无效的任务状态：{status}")

            with get_db() as db:
                task = db.query(WechatTask).filter(WechatTask.id == task_id).first()
                if task:
                    task.status = status
                    task.last_status_at = datetime.now()
                    task.updated_at = datetime.now()
                    db.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"更新任务状态失败：{e}")
            return False

    def _recognize_message_type(self, text: str) -> str:
        if self.recognize_order(text):
            return "order"
        elif self.recognize_shipment(text):
            return "shipment"
        else:
            return "unknown"

    def _process_order_message(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw_text = task.get("raw_text", "")
            order_info = self.recognize_order(raw_text)
            if not order_info:
                return {"success": False, "message": "无法解析订单信息"}

            product_name = order_info.get("product", "")
            quantity = order_info.get("quantity", 0)
            unit = order_info.get("unit", "")

            logger.info(f"收到订单：产品={product_name}, 数量={quantity} {unit}, 原始消息={raw_text}")

            return {"success": True, "message": "订单已记录", "order_info": order_info}

        except Exception as e:
            logger.exception(f"处理订单消息失败：{e}")
            return {"success": False, "message": f"处理失败：{str(e)}"}

    def _process_shipment_message(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw_text = task.get("raw_text", "")
            shipment_info = self.recognize_shipment(raw_text)
            if not shipment_info:
                return {"success": False, "message": "无法解析发货单信息"}

            products = shipment_info.get("products")
            content = shipment_info.get("content", "")

            logger.info(f"收到发货单：内容={content}, 产品={products}, 原始消息={raw_text}")

            return {"success": True, "message": "发货单已记录", "shipment_info": shipment_info}

        except Exception as e:
            logger.exception(f"处理发货单消息失败：{e}")
            return {"success": False, "message": f"处理失败：{str(e)}"}


_wechat_task_app_service: Optional[WechatTaskApplicationService] = None


def get_wechat_task_app_service() -> WechatTaskApplicationService:
    global _wechat_task_app_service
    if _wechat_task_app_service is None:
        _wechat_task_app_service = WechatTaskApplicationService()
    return _wechat_task_app_service
