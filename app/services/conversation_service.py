# -*- coding: utf-8 -*-
"""
对话服务模块

提供对话历史和会话管理的业务逻辑。
"""

import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional, Tuple

from app.db.models import AIConversation, AIConversationSession
from app.db.session import get_db

logger = logging.getLogger(__name__)


class ConversationService:
    """对话服务类"""

    def __init__(self):
        """初始化对话服务"""
        pass

    def save_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        intent: str = "",
        metadata: str = ""
    ) -> int:
        """
        保存对话消息

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            role: 角色（user/assistant）
            content: 消息内容
            intent: 意图
            metadata: 元数据

        Returns:
            消息 ID
        """
        with get_db() as db:
            try:
                # 保存消息
                conversation = AIConversation(
                    session_id=session_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    intent=intent,
                    conversation_metadata=metadata,
                    created_at=datetime.now()
                )
                db.add(conversation)
                db.flush()

                # 更新或创建会话
                session = db.query(AIConversationSession).filter(
                    AIConversationSession.session_id == session_id
                ).first()

                if session:
                    session.message_count += 1
                    session.last_message_at = datetime.now()
                else:
                    session = AIConversationSession(
                        session_id=session_id,
                        user_id=user_id,
                        message_count=1,
                        last_message_at=datetime.now(),
                        created_at=datetime.now()
                    )
                    db.add(session)

                db.commit()
                return conversation.id
            except Exception as e:
                db.rollback()
                logger.error(f"保存对话消息失败: {e}")
                raise

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Tuple]:
        """
        获取会话消息

        Args:
            session_id: 会话 ID
            limit: 返回数量限制

        Returns:
            消息列表，每个元素是元组 (id, session_id, user_id, role, content, intent, metadata, created_at)
        """
        with get_db() as db:
            try:
                messages = db.query(AIConversation).filter(
                    AIConversation.session_id == session_id
                ).order_by(AIConversation.created_at.asc()).limit(limit).all()

                result = []
                for msg in messages:
                    result.append((
                        msg.id,
                        msg.session_id,
                        msg.user_id,
                        msg.role,
                        msg.content,
                        msg.intent or "",
                        msg.conversation_metadata or "",
                        msg.created_at
                    ))
                return result
            except Exception as e:
                logger.error(f"获取会话消息失败: {e}")
                raise

    def get_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Tuple]:
        """
        获取会话列表

        Args:
            user_id: 用户 ID（可选）
            limit: 返回数量限制

        Returns:
            会话列表，每个元素是元组 (id, session_id, user_id, title, summary, message_count, last_message_at, created_at)
        """
        with get_db() as db:
            try:
                query = db.query(AIConversationSession)

                if user_id:
                    query = query.filter(
                        (AIConversationSession.user_id == user_id) |
                        (AIConversationSession.user_id.is_(None))
                    )

                sessions = query.order_by(
                    AIConversationSession.last_message_at.desc()
                ).limit(limit).all()

                result = []
                for session in sessions:
                    result.append((
                        session.id,
                        session.session_id,
                        session.user_id,
                        session.title,
                        session.summary,
                        session.message_count,
                        session.last_message_at,
                        session.created_at
                    ))
                return result
            except Exception as e:
                logger.error(f"获取会话列表失败: {e}")
                raise

    def update_session_title(self, session_id: str, title: str) -> bool:
        """
        更新会话标题

        Args:
            session_id: 会话 ID
            title: 新标题

        Returns:
            是否更新成功
        """
        with get_db() as db:
            try:
                session = db.query(AIConversationSession).filter(
                    AIConversationSession.session_id == session_id
                ).first()

                if session:
                    session.title = title
                    db.commit()
                    return True
                return False
            except Exception as e:
                db.rollback()
                logger.error(f"更新会话标题失败: {e}")
                raise

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        with get_db() as db:
            try:
                # 删除会话的所有消息
                db.query(AIConversation).filter(
                    AIConversation.session_id == session_id
                ).delete()

                # 删除会话
                result = db.query(AIConversationSession).filter(
                    AIConversationSession.session_id == session_id
                ).delete()

                db.commit()
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"删除会话失败：{e}")
                raise

    def create_session(self, user_id: str = 'default', title: str = None) -> str:
        """
        创建新会话

        Args:
            user_id: 用户 ID
            title: 会话标题（可选）

        Returns:
            新创建的会话 ID
        """
        with get_db() as db:
            try:
                session_id = str(uuid.uuid4())
                session = AIConversationSession(
                    session_id=session_id,
                    user_id=user_id,
                    title=title,
                    message_count=0,
                    last_message_at=datetime.now(),
                    created_at=datetime.now()
                )
                db.add(session)
                db.commit()
                return session_id
            except Exception as e:
                db.rollback()
                logger.error(f"创建会话失败：{e}")
                raise


# 全局服务实例
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """获取对话服务单例"""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
