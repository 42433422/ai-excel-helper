# -*- coding: utf-8 -*-
"""
IntentContext - 任务上下文

管理 pending 状态的粘接和续接机制

核心算法：
1. _should_adopt_new_intent() - 决定是否采纳新意图
2. merge_slots() - 合并槽位并更新状态
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AdoptionReason(Enum):
    """采纳原因枚举"""
    NEW_TASK = "new_task"                    # 新任务
    MERGE_SLOTS = "merge_slots"              # 槽位合并（相同意图续接）
    SPECIAL_INTENT_PRESERVED = "special_intent_preserved"  # 特殊意图保留
    INTENT_PRESERVED = "intent_preserved"    # 意图保留
    LOW_PRIORITY_SWITCH = "low_priority_switch"  # 低优先级切换
    SWITCH_REQUESTED = "switch_requested"    # 请求切换


SPECIAL_INTENTS = {"greeting", "goodbye", "help", "confirmation", "negation"}

LOW_PRIORITY_INTENTS = {"products", "customers", "shipments", "materials", "template_query"}

HIGH_PRIORITY_INTENTS = {"shipment_generate", "wechat_send", "print_label"}


@dataclass
class PendingIntent:
    """
    待确认意图

    扩展字段：
    - created_at: 创建时间，用于超时判断
    - last_updated_at: 最后更新时间
    - turn_count: 续接次数统计
    """
    intent: str
    slots: Dict[str, Any]
    missing_slots: List[str]
    created_at: float = field(default_factory=time.time)
    source: str = "unknown"
    last_updated_at: float = field(default_factory=time.time)
    turn_count: int = 1

    def is_expired(self, max_age_seconds: float = 300) -> bool:
        """检查是否过期（5分钟无操作）"""
        return time.time() - self.last_updated_at > max_age_seconds

    def merge_slots(self, new_slots: Dict[str, Any]) -> 'PendingIntent':
        """
        合并新槽位到 pending

        Returns:
            新的 PendingIntent（turn_count + 1）
        """
        merged = self.slots.copy()
        merged.update(new_slots)

        still_missing = [s for s in self.missing_slots if not merged.get(s)]

        return PendingIntent(
            intent=self.intent,
            slots=merged,
            missing_slots=still_missing,
            created_at=self.created_at,
            source=self.source,
            last_updated_at=time.time(),
            turn_count=self.turn_count + 1
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "intent": self.intent,
            "slots": self.slots,
            "missing_slots": self.missing_slots,
            "created_at": self.created_at,
            "source": self.source,
            "last_updated_at": self.last_updated_at,
            "turn_count": self.turn_count,
            "is_expired": self.is_expired(),
        }


class IntentContext:
    """
    任务上下文管理器

    职责：
    1. 存储和管理 pending 状态
    2. 决策是否采纳新意图
    3. 槽位合并
    4. 超时清理

    使用依赖注入模式，支持通过容器管理生命周期。
    """

    def __init__(self) -> None:
        self._pending_store: Dict[str, PendingIntent] = {}

    def set_pending(self, user_id: str, pending: PendingIntent) -> None:
        """
        设置待确认意图

        Args:
            user_id: 用户ID
            pending: 待确认意图
        """
        self._pending_store[user_id] = pending
        logger.info(
            f"[INTENT_CONTEXT] Set pending: user={user_id}, "
            f"intent={pending.intent}, missing={pending.missing_slots}, "
            f"turn_count={pending.turn_count}"
        )
        self._notify_update(user_id, pending, "created")

    def get_pending(self, user_id: str) -> Optional[PendingIntent]:
        """
        获取待确认意图

        会自动清理过期的 pending

        Args:
            user_id: 用户ID

        Returns:
            PendingIntent 或 None（如果不存在或已过期）
        """
        pending = self._pending_store.get(user_id)

        if pending is None:
            return None

        if pending.is_expired():
            logger.info(f"[INTENT_CONTEXT] Pending expired: user={user_id}, intent={pending.intent}")
            self.clear_pending(user_id)
            return None

        return pending

    def clear_pending(self, user_id: str, reason: str = "completed") -> None:
        """清除待确认意图"""
        if user_id in self._pending_store:
            old_pending = self._pending_store[user_id]
            del self._pending_store[user_id]
            logger.info(
                f"[INTENT_CONTEXT] Cleared pending: user={user_id}, "
                f"intent={old_pending.intent}, turn_count={old_pending.turn_count}"
            )
            self._notify_cleared(user_id, reason)

    def has_pending(self, user_id: str) -> bool:
        """检查是否有 pending"""
        return self.get_pending(user_id) is not None

    def merge_slots(self, user_id: str, new_slots: Dict[str, Any]) -> Optional[PendingIntent]:
        """
        合并新槽位到 pending

        Args:
            user_id: 用户ID
            new_slots: 新提取的槽位

        Returns:
            更新后的 PendingIntent 或 None
        """
        pending = self.get_pending(user_id)
        if not pending:
            return None

        updated = pending.merge_slots(new_slots)
        self.set_pending(user_id, updated)
        self._notify_update(user_id, updated, "updated")
        return updated

    def should_adopt_new_intent(
        self,
        new_intent: str,
        pending: Optional[PendingIntent]
    ) -> Tuple[bool, AdoptionReason, Optional[PendingIntent]]:
        """
        决定是否采纳新意图

        核心算法：
        1. 无 pending → 采纳新任务
        2. 特殊意图（问候/再见/帮助）→ 保留 pending
        3. 新意图 == pending.intent → 槽位合并续接
        4. pending.turn_count >= 3 → 可能卡住了，询问是否切换
        5. 低优先级意图 → 可以切换
        6. 默认 → 保留 pending

        Args:
            new_intent: 新识别的意图
            pending: 当前的 pending

        Returns:
            (是否采纳, 原因, 更新后的 pending)
        """
        if not pending:
            return True, AdoptionReason.NEW_TASK, None

        if new_intent in SPECIAL_INTENTS:
            return False, AdoptionReason.SPECIAL_INTENT_PRESERVED, pending

        if new_intent == pending.intent:
            return True, AdoptionReason.MERGE_SLOTS, pending

        if pending.turn_count >= 3:
            return True, AdoptionReason.SWITCH_REQUESTED, pending

        if new_intent in LOW_PRIORITY_INTENTS and pending.intent in HIGH_PRIORITY_INTENTS:
            return False, AdoptionReason.INTENT_PRESERVED, pending

        if pending.intent in LOW_PRIORITY_INTENTS and new_intent in HIGH_PRIORITY_INTENTS:
            return True, AdoptionReason.LOW_PRIORITY_SWITCH, pending

        return False, AdoptionReason.INTENT_PRESERVED, pending

    def get_pending_summary(self, user_id: str) -> Dict[str, Any]:
        """获取 pending 摘要"""
        pending = self.get_pending(user_id)
        if not pending:
            return {"has_pending": False}

        return {
            "has_pending": True,
            "intent": pending.intent,
            "slots": pending.slots,
            "missing_slots": pending.missing_slots,
            "turn_count": pending.turn_count,
            "age_seconds": time.time() - pending.created_at,
            "is_near_expiry": (time.time() - pending.last_updated_at) > 240,
        }

    def cleanup_expired(self) -> int:
        """清理所有过期的 pending"""
        expired_users = []
        for user_id, pending in self._pending_store.items():
            if pending.is_expired():
                expired_users.append(user_id)

        for user_id in expired_users:
            self.clear_pending(user_id)

        if expired_users:
            logger.info(f"[INTENT_CONTEXT] Cleaned up {len(expired_users)} expired pending")

        return len(expired_users)

    def get_all_pending_count(self) -> int:
        """获取当前 pending 数量"""
        return len(self._pending_store)

    def _notify_update(self, user_id: str, pending: PendingIntent, event: str) -> None:
        """通知 pending 状态变化"""
        try:
            notifier = self._get_notifier()
            if notifier:
                pending_data = pending.to_dict()
                if event == "created":
                    notifier.notify_pending_created(user_id, pending_data)
                elif event == "updated":
                    notifier.notify_pending_updated(user_id, pending_data)
        except Exception as e:
            logger.warning(f"[INTENT_CONTEXT] Failed to notify: {e}")

    def _notify_cleared(self, user_id: str, reason: str) -> None:
        """通知 pending 清除"""
        try:
            notifier = self._get_notifier()
            if notifier:
                notifier.notify_pending_cleared(user_id, reason)
        except Exception as e:
            logger.warning(f"[INTENT_CONTEXT] Failed to notify: {e}")

    def _notify_preserved(self, user_id: str, pending: PendingIntent, action: str) -> None:
        """通知 pending 保留（特殊意图时）"""
        try:
            notifier = self._get_notifier()
            if notifier:
                pending_data = pending.to_dict()
                notifier.notify_pending_preserved(user_id, pending_data, action)
        except Exception as e:
            logger.warning(f"[INTENT_CONTEXT] Failed to notify: {e}")

    def _get_notifier(self):
        """懒加载获取通知器"""
        if not hasattr(self, '_notifier'):
            try:
                from app.routes.context_api import get_context_notifier
                self._notifier = get_context_notifier()
            except ImportError:
                self._notifier = None
        return self._notifier


class IntentContextContainer:
    _instance: Optional[IntentContext] = None

    @classmethod
    def get_instance(cls) -> IntentContext:
        if cls._instance is None:
            cls._instance = IntentContext()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None


def get_intent_context() -> IntentContext:
    """获取 IntentContext 单例（向后兼容）"""
    return IntentContextContainer.get_instance()
