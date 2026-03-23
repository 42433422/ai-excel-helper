# -*- coding: utf-8 -*-
"""
ChatContext - 聊天上下文

管理对话历史和重复检测机制

核心算法：
1. _make_message_fingerprint() - 消息指纹（精确匹配）
2. _make_semantic_fingerprint() - 语义指纹（意图+槽位）
3. _is_duplicate() - 重复检测
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ChatTurn:
    """
    对话轮次

    记录单轮对话的信息
    """
    user_id: str
    message: str
    intent: Optional[str]
    tool_key: Optional[str]
    slots: Dict[str, Any]
    response_text: Optional[str]
    timestamp: float = field(default_factory=time.time)
    is_exact_duplicate: bool = False
    is_semantic_duplicate: bool = False

    @property
    def message_fingerprint(self) -> str:
        """消息指纹（精确匹配用）"""
        return hashlib.md5(
            self.message.strip().lower().encode()
        ).hexdigest()[:16]

    def make_semantic_fingerprint(self) -> str:
        """语义指纹（意图+关键槽位）"""
        key_parts = [
            self.intent or "",
            self.tool_key or "",
        ]

        if self.slots:
            key_slots = []
            for k in sorted(self.slots.keys()):
                v = self.slots.get(k)
                if v and str(v).strip():
                    key_slots.append(f"{k}={v}")
            key_parts.append("|".join(key_slots))

        fingerprint = "|".join(key_parts)
        return hashlib.md5(fingerprint.encode()).hexdigest()[:16]


class ChatContext:
    """
    聊天上下文管理器

    职责：
    1. 存储对话历史（最近 N 条）
    2. 重复消息检测（精确匹配 + 语义匹配）
    3. 缓存响应结果

    使用依赖注入模式，支持通过容器管理生命周期。
    """

    MAX_HISTORY_SIZE = 10
    DUPLICATE_WINDOW = 3
    EXACT_DUPLICATE_TTL = 5.0

    def __init__(self) -> None:
        self._history: Dict[str, List[ChatTurn]] = {}
        self._exact_cache: Dict[str, Tuple[Any, float]] = {}
        self._semantic_cache: Dict[str, Tuple[Any, float]] = {}

    def add_turn(self, user_id: str, turn: ChatTurn) -> None:
        """
        添加对话轮次

        Args:
            user_id: 用户ID
            turn: 对话轮次
        """
        if user_id not in self._history:
            self._history[user_id] = []

        self._history[user_id].append(turn)

        if len(self._history[user_id]) > self.MAX_HISTORY_SIZE:
            self._history[user_id] = self._history[user_id][-self.MAX_HISTORY_SIZE:]

        self._update_semantic_cache(user_id, turn)

        logger.debug(
            f"[CHAT_CONTEXT] Added turn: user={user_id}, "
            f"intent={turn.intent}, history_size={len(self._history[user_id])}"
        )

    def get_recent_turns(self, user_id: str, limit: int = 10) -> List[ChatTurn]:
        """
        获取最近的对话轮次

        Args:
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            ChatTurn 列表
        """
        turns = self._history.get(user_id, [])
        return turns[-limit:] if limit > 0 else turns

    def get_recent_intents(self, user_id: str, limit: int = 3) -> List[str]:
        """
        获取最近的意图列表

        Args:
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            意图列表
        """
        turns = self.get_recent_turns(user_id, limit)
        return [t.intent for t in turns if t.intent]

    def clear_history(self, user_id: str) -> None:
        """清除用户的历史记录"""
        if user_id in self._history:
            del self._history[user_id]
            logger.info(f"[CHAT_CONTEXT] Cleared history: user={user_id}")

    def _update_semantic_cache(self, user_id: str, turn: ChatTurn) -> None:
        """更新语义缓存"""
        if not turn.intent:
            return

        fingerprint = turn.make_semantic_fingerprint()
        now = time.time()

        cache_key = f"{user_id}:{fingerprint}"
        self._semantic_cache[cache_key] = (turn.response_text, now)

        self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """清理过期的缓存"""
        now = time.time()
        expired_keys = []

        for key, ( _, timestamp) in self._semantic_cache.items():
            if now - timestamp > 300:
                expired_keys.append(key)

        for key in expired_keys:
            del self._semantic_cache[key]

        expired_exact = [
            key for key, (_, timestamp) in self._exact_cache.items()
            if now - timestamp > self.EXACT_DUPLICATE_TTL
        ]

        for key in expired_exact:
            del self._exact_cache[key]

    def is_duplicate(
        self,
        user_id: str,
        message: str,
        intent: Optional[str] = None,
        tool_key: Optional[str] = None,
        slots: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], bool]:
        """
        检测是否为重复消息

        检测策略：
        1. 精确匹配（消息指纹）- 5秒内有效
        2. 语义匹配（意图+槽位）- 只在最近3条内检测

        Args:
            user_id: 用户ID
            message: 用户消息
            intent: 识别到的意图
            tool_key: 工具 key
            slots: 槽位信息

        Returns:
            (是否重复, 缓存的响应文本, 是否是精确重复)
        """
        msg_fingerprint = hashlib.md5(
            message.strip().lower().encode()
        ).hexdigest()[:16]

        exact_key = f"{user_id}:{msg_fingerprint}"
        if exact_key in self._exact_cache:
            cached_response, timestamp = self._exact_cache[exact_key]
            if time.time() - timestamp <= self.EXACT_DUPLICATE_TTL:
                logger.info(
                    f"[CHAT_CONTEXT] Exact duplicate detected: user={user_id}, "
                    f"msg={message[:30]}..."
                )
                return True, cached_response, True

        if intent:
            semantic_key = f"{user_id}:{intent}:{tool_key or ''}"

            if slots:
                slot_parts = []
                for k in sorted(slots.keys()):
                    v = slots.get(k)
                    if v and str(v).strip():
                        slot_parts.append(f"{k}={v}")
                if slot_parts:
                    semantic_key += ":" + "|".join(slot_parts)

            recent_turns = self.get_recent_turns(user_id, self.DUPLICATE_WINDOW)
            for turn in recent_turns:
                if turn.make_semantic_fingerprint() == hashlib.md5(
                    f"{intent}:{tool_key or ''}".encode()
                ).hexdigest()[:16]:
                    if turn.response_text:
                        logger.info(
                            f"[CHAT_CONTEXT] Semantic duplicate detected: user={user_id}, "
                            f"intent={intent}"
                        )
                        return True, turn.response_text, False

        return False, None, False

    def cache_response(
        self,
        user_id: str,
        message: str,
        response_text: str
    ) -> None:
        """
        缓存响应结果

        Args:
            user_id: 用户ID
            message: 用户消息
            response_text: 响应文本
        """
        msg_fingerprint = hashlib.md5(
            message.strip().lower().encode()
        ).hexdigest()[:16]

        exact_key = f"{user_id}:{msg_fingerprint}"
        self._exact_cache[exact_key] = (response_text, time.time())

        self._cleanup_cache()

    def get_history_summary(self, user_id: str) -> Dict[str, Any]:
        """获取历史摘要"""
        turns = self.get_recent_turns(user_id)
        if not turns:
            return {"has_history": False, "count": 0}

        return {
            "has_history": True,
            "count": len(turns),
            "recent_intents": [t.intent for t in turns[-3:] if t.intent],
            "last_message": turns[-1].message if turns else None,
            "last_intent": turns[-1].intent if turns else None,
        }

    def cleanup_old_history(self, max_age_seconds: float = 3600) -> int:
        """
        清理过期的历史记录

        Args:
            max_age_seconds: 最大保留时间

        Returns:
            清理的记录数
        """
        now = time.time()
        cleaned = 0

        for user_id, turns in list(self._history.items()):
            original_len = len(turns)
            self._history[user_id] = [
                t for t in turns
                if now - t.timestamp <= max_age_seconds
            ]
            cleaned += original_len - len(self._history[user_id])

            if not self._history[user_id]:
                del self._history[user_id]

        if cleaned > 0:
            logger.info(f"[CHAT_CONTEXT] Cleaned up {cleaned} old history entries")

        return cleaned

    def get_all_users_count(self) -> int:
        """获取有历史记录的用户数"""
        return len(self._history)


class ChatContextContainer:
    _instance: Optional[ChatContext] = None

    @classmethod
    def get_instance(cls) -> ChatContext:
        if cls._instance is None:
            cls._instance = ChatContext()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None


def get_chat_context() -> ChatContext:
    """获取 ChatContext 单例（向后兼容）"""
    return ChatContextContainer.get_instance()
