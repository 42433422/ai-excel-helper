"""
微信相关 Celery 任务模块

包含微信消息处理、任务扫描等异步任务。
"""

import logging
from typing import Any, Dict, List

from app.extensions import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_wechat_message(self, message_data: Dict[str, Any]) -> bool:
    """
    处理单条微信消息
    
    Args:
        message_data: 消息数据字典，包含：
            - contact_id: 联系人 ID
            - username: 用户名
            - display_name: 显示名称
            - message_id: 消息 ID
            - raw_text: 原始消息文本
            - msg_timestamp: 消息时间戳
            
    Returns:
        是否处理成功
    """
    try:
        logger.info(f"开始处理微信消息：{message_data.get('message_id')}")
        
        # 调用服务层处理消息（基于 task_id）
        from app.services import get_wechat_task_service
        service = get_wechat_task_service()
        task_id = message_data.get("id")
        result = service.process_message(task_id)
        
        logger.info(f"微信消息处理完成：{result}")
        return result.get('success', False)
        
    except Exception as e:
        logger.exception(f"处理微信消息失败：{e}")
        # 重试逻辑
        try:
            self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f"微信消息处理达到最大重试次数：{message_data.get('message_id')}")
            return False


@celery_app.task(bind=True, max_retries=3)
def scan_wechat_messages(self, contact_id: int | None = None, limit: int = 20) -> int:
    """
    扫描微信消息并创建任务
    
    Args:
        contact_id: 联系人 ID（可选，为 None 时扫描所有联系人）
        limit: 扫描数量限制
        
    Returns:
        发现的新消息数量
    """
    try:
        logger.info(f"开始扫描微信消息，联系人 ID: {contact_id}, 限制：{limit}")

        from app.services import get_wechat_task_service

        service = get_wechat_task_service()
        new_tasks = service.scan_messages(contact_id=contact_id, limit=limit)

        # 异步处理每条新任务
        for t in new_tasks:
            try:
                process_wechat_message.delay({"id": t.get("id")})
            except Exception as e:
                logger.warning("派发微信消息处理任务失败 task_id=%s: %s", t.get("id"), e)

        new_count = len(new_tasks)
        logger.info(f"扫描完成，发现 {new_count} 条新消息")
        return new_count
        
    except Exception as e:
        logger.exception(f"扫描微信消息失败：{e}")
        try:
            self.retry(exc=e, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error("扫描微信消息达到最大重试次数")
            return 0


@celery_app.task
def cleanup_old_tasks(days: int = 30) -> int:
    """
    清理旧任务
    
    Args:
        days: 保留天数
        
    Returns:
        清理的任务数量
    """
    try:
        logger.info(f"开始清理 {days} 天前的旧任务")
        
        import sqlite3

        from app.db.init_db import get_db_path
        
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 删除 30 天前的已完成/已忽略任务
        cursor.execute(
            """
            DELETE FROM wechat_tasks 
            WHERE status IN ('confirmed', 'done', 'ignored')
            AND created_at < datetime('now', '-' || ? || ' days')
            """,
            (days,)
        )
        
        cleaned_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"清理完成，共清理 {cleaned_count} 个任务")
        return cleaned_count
        
    except Exception as e:
        logger.exception(f"清理旧任务失败：{e}")
        return 0


# 定期任务配置示例
# 在 celery_app.py 或配置文件中添加：
# CELERY_BEAT_SCHEDULE = {
#     'scan-wechat-messages': {
#         'task': 'app.tasks.wechat_tasks.scan_wechat_messages',
#         'schedule': 30.0,  # 每 30 秒扫描一次
#         'options': {'limit': 20}
#     },
#     'cleanup-old-tasks': {
#         'task': 'app.tasks.wechat_tasks.cleanup_old_tasks',
#         'schedule': crontab(hour=2, minute=0),  # 每天凌晨 2 点执行
#         'options': {'days': 30}
#     },
# }
