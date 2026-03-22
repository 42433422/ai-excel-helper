# -*- coding: utf-8 -*-
"""
用户记忆服务 - UserMemoryService

提供跨会话的长期记忆能力，包括：
- 用户偏好记忆
- 操作模式学习
- 上下文摘要
- 反馈记录与难例挖掘

支持 SQLite 和 JSON 文件两种存储后端。

此模块已迁移到 app/utils/
"""

import hashlib
import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEMORY_DIR = os.path.join(BASE_DIR, "user_memory")
JSON_MEMORY_PATH = os.path.join(MEMORY_DIR, "memory_store.json")

MAX_FEEDBACK_HISTORY = 100
MAX_FREQUENT_ACTIONS = 20
MAX_CONTEXT_SUMMARIES = 10


@dataclass
class ActionPattern:
    pattern: str
    intent: str
    slots: Dict[str, Any]
    frequency: int = 1
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionPattern':
        return cls(**data)


@dataclass
class FeedbackRecord:
    timestamp: str
    message: str
    recognized_intent: str
    user_feedback: str
    corrected_intent: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackRecord':
        return cls(**data)


@dataclass
class ContextSummary:
    timestamp: str
    intent: str
    slots: Dict[str, Any]
    message: str
    turn_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextSummary':
        return cls(**data)


@dataclass
class UserMemory:
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    frequent_actions: List[Dict[str, Any]] = field(default_factory=list)
    historical_contexts: List[Dict[str, Any]] = field(default_factory=list)
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserMemory':
        return cls(**data)


class UserMemoryStore:
    """用户记忆存储后端"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, storage_type: str = "json"):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.storage_type = storage_type
        self._memory_cache: Dict[str, UserMemory] = {}
        self._cache_dirty: Dict[str, bool] = {}
        self._load_all_memories()
        self._initialized = True

    def _load_all_memories(self) -> None:
        """加载所有用户记忆"""
        if self.storage_type == "json" and os.path.exists(JSON_MEMORY_PATH):
            try:
                with open(JSON_MEMORY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, memory_data in data.items():
                        self._memory_cache[user_id] = UserMemory.from_dict(memory_data)
                logger.info(f"从 {JSON_MEMORY_PATH} 加载了 {len(self._memory_cache)} 个用户记忆")
            except Exception as e:
                logger.error(f"加载用户记忆失败: {e}")
                self._memory_cache = {}

    def _save_all_memories(self) -> None:
        """保存所有用户记忆到磁盘"""
        if self.storage_type != "json":
            return

        try:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            data = {user_id: memory.to_dict() for user_id, memory in self._memory_cache.items()}
            with open(JSON_MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存 {len(self._memory_cache)} 个用户记忆到 {JSON_MEMORY_PATH}")
        except Exception as e:
            logger.error(f"保存用户记忆失败: {e}")

    def get_memory(self, user_id: str) -> Optional[UserMemory]:
        """获取用户记忆"""
        if user_id not in self._memory_cache:
            self._memory_cache[user_id] = UserMemory(user_id=user_id)
        return self._memory_cache[user_id]

    def save_memory(self, user_id: str, memory: UserMemory) -> None:
        """保存用户记忆"""
        memory.updated_at = datetime.now().isoformat()
        self._memory_cache[user_id] = memory
        self._cache_dirty[user_id] = True

        if self._should_persist():
            self._save_all_memories()
            self._cache_dirty[user_id] = False

    def _should_persist(self) -> bool:
        """判断是否应该持久化"""
        return any(self._cache_dirty.values())


class UserMemoryService:
    """
    用户记忆服务

    提供：
    - add_preference: 添加用户偏好
    - get_preference: 获取用户偏好
    - record_action: 记录用户操作
    - get_recent_actions: 获取最近操作
    - get_similar_pattern: 查找相似模式
    - add_feedback: 添加反馈
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, storage_type: str = "json"):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._store = UserMemoryStore(storage_type=storage_type)
        self._initialized = True
        logger.info("用户记忆服务已初始化")

    def add_preference(self, user_id: str, key: str, value: Any) -> None:
        """
        添加用户偏好

        Args:
            user_id: 用户ID
            key: 偏好键 (如 "favorite_customer", "default_template")
            value: 偏好值
        """
        memory = self._store.get_memory(user_id)
        if memory is None:
            memory = UserMemory(user_id=user_id)

        memory.preferences[key] = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
            "count": memory.preferences.get(key, {}).get("count", 0) + 1
        }

        self._store.save_memory(user_id, memory)
        logger.debug(f"用户 {user_id} 偏好已更新: {key} = {value}")

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        获取用户偏好

        Args:
            user_id: 用户ID
            key: 偏好键
            default: 默认值

        Returns:
            偏好值或默认值
        """
        memory = self._store.get_memory(user_id)
        if memory and key in memory.preferences:
            return memory.preferences[key].get("value", default)
        return default

    def get_all_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户所有偏好"""
        memory = self._store.get_memory(user_id)
        if memory:
            return {k: v.get("value") for k, v in memory.preferences.items()}
        return {}

    def record_action(
        self,
        user_id: str,
        intent: str,
        slots: Dict[str, Any],
        message: str = ""
    ) -> None:
        """
        记录用户操作模式

        Args:
            user_id: 用户ID
            intent: 意图类型
            slots: 槽位信息
            message: 原始消息
        """
        memory = self._store.get_memory(user_id)
        if memory is None:
            memory = UserMemory(user_id=user_id)

        pattern_key = self._make_pattern_key(intent, slots)
        existing_pattern = None
        pattern_idx = -1

        for idx, action in enumerate(memory.frequent_actions):
            if action.get("pattern") == pattern_key:
                existing_pattern = action
                pattern_idx = idx
                break

        if existing_pattern:
            existing_pattern["frequency"] += 1
            existing_pattern["last_used"] = datetime.now().isoformat()
            existing_pattern["confidence"] = min(0.99, existing_pattern["confidence"] + 0.05)
            memory.frequent_actions[pattern_idx] = existing_pattern
        else:
            new_pattern = ActionPattern(
                pattern=pattern_key,
                intent=intent,
                slots=slots,
                frequency=1,
                last_used=datetime.now().isoformat(),
                confidence=0.5
            )
            memory.frequent_actions.insert(0, new_pattern.to_dict())

        memory.frequent_actions.sort(key=lambda x: x.get("frequency", 0), reverse=True)
        memory.frequent_actions = memory.frequent_actions[:MAX_FREQUENT_ACTIONS]

        self._save_context_summary(memory, intent, slots, message)

        self._store.save_memory(user_id, memory)
        logger.debug(f"用户 {user_id} 操作已记录: intent={intent}, slots={slots}")

    def _make_pattern_key(self, intent: str, slots: Dict[str, Any]) -> str:
        """生成模式唯一键"""
        key_parts = [intent]
        important_slots = ["unit_name", "product_name", "model_number"]
        for slot_key in important_slots:
            if slot_key in slots and slots[slot_key]:
                key_parts.append(f"{slot_key}={slots[slot_key]}")
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]

    def _save_context_summary(
        self,
        memory: UserMemory,
        intent: str,
        slots: Dict[str, Any],
        message: str
    ) -> None:
        """保存上下文摘要"""
        summary = ContextSummary(
            timestamp=datetime.now().isoformat(),
            intent=intent,
            slots=slots,
            message=message[:100] if message else "",
            turn_count=1
        )
        memory.historical_contexts.insert(0, summary.to_dict())
        memory.historical_contexts = memory.historical_contexts[:MAX_CONTEXT_SUMMARIES]

    def get_recent_actions(
        self,
        user_id: str,
        limit: int = 5,
        intent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取最近操作模式

        Args:
            user_id: 用户ID
            limit: 返回数量
            intent_filter: 意图过滤器

        Returns:
            最近操作列表
        """
        memory = self._store.get_memory(user_id)
        if not memory:
            return []

        actions = memory.frequent_actions
        if intent_filter:
            actions = [a for a in actions if a.get("intent") == intent_filter]

        return actions[:limit]

    def get_similar_pattern(
        self,
        user_id: str,
        intent: str,
        slots: Dict[str, Any],
        threshold: float = 0.2
    ) -> Optional[Dict[str, Any]]:
        """
        查找相似的操作模式

        Args:
            user_id: 用户ID
            intent: 目标意图
            slots: 当前槽位
            threshold: 相似度阈值

        Returns:
            相似模式或 None
        """
        memory = self._store.get_memory(user_id)
        if not memory:
            return None

        best_match = None
        best_score = 0.0

        for action in memory.frequent_actions:
            if action.get("intent") != intent:
                continue

            score = self._calculate_similarity(slots, action.get("slots", {}))
            action_confidence = action.get("confidence", 0.5)

            if score >= 0.5:
                combined_score = score
            else:
                combined_score = score * action_confidence

            if combined_score > best_score and combined_score >= threshold:
                best_score = combined_score
                best_match = action

        if best_match:
            best_match["match_score"] = round(best_score, 3)

        return best_match

    def _calculate_similarity(
        self,
        slots1: Dict[str, Any],
        slots2: Dict[str, Any]
    ) -> float:
        """计算槽位相似度"""
        if not slots1 and not slots2:
            return 1.0

        important_keys = ["unit_name", "spec", "model_number", "quantity", "product_name"]
        match_count = 0
        total_count = 0

        for key in important_keys:
            v1 = slots1.get(key, "") or slots1.get(key)
            v2 = slots2.get(key, "") or slots2.get(key)
            if v1 and v2:
                total_count += 1
                if str(v1) == str(v2):
                    match_count += 1

        if total_count == 0:
            return 0.5

        return match_count / total_count

    def add_feedback(
        self,
        user_id: str,
        message: str,
        recognized_intent: str,
        feedback: str,
        corrected_intent: Optional[str] = None,
        slots: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加用户反馈

        Args:
            user_id: 用户ID
            message: 用户消息
            recognized_intent: 系统识别的意图
            feedback: 反馈类型 (confirmed/negated/corrected)
            corrected_intent: 正确意图（当 feedback=corrected 时）
            slots: 槽位信息
        """
        memory = self._store.get_memory(user_id)
        if memory is None:
            memory = UserMemory(user_id=user_id)

        record = FeedbackRecord(
            timestamp=datetime.now().isoformat(),
            message=message[:200] if message else "",
            recognized_intent=recognized_intent,
            user_feedback=feedback,
            corrected_intent=corrected_intent,
            slots=slots or {}
        )
        memory.feedback_history.insert(0, record.to_dict())
        memory.feedback_history = memory.feedback_history[:MAX_FEEDBACK_HISTORY]

        self._adjust_pattern_weights(memory, recognized_intent, corrected_intent, feedback)

        self._store.save_memory(user_id, memory)
        logger.debug(f"用户 {user_id} 反馈已记录: feedback={feedback}, recognized={recognized_intent}")

    def _adjust_pattern_weights(
        self,
        memory: UserMemory,
        recognized_intent: str,
        corrected_intent: Optional[str],
        feedback: str
    ) -> None:
        """调整模式权重"""
        weight_delta = 0
        target_intent = recognized_intent

        if feedback == "confirmed":
            weight_delta = 0.1
        elif feedback == "negated":
            weight_delta = -0.15
        elif feedback == "corrected" and corrected_intent:
            weight_delta = -0.1
            target_intent = corrected_intent

        for action in memory.frequent_actions:
            if action.get("intent") == target_intent:
                new_confidence = action.get("confidence", 0.5) + weight_delta
                action["confidence"] = max(0.1, min(0.99, new_confidence))

    def get_feedback_stats(self, user_id: str) -> Dict[str, Any]:
        """获取反馈统计"""
        memory = self._store.get_memory(user_id)
        if not memory:
            return {"total": 0, "confirmed": 0, "negated": 0, "corrected": 0}

        feedback_counts = defaultdict(int)
        intent_error_rates = defaultdict(lambda: {"total": 0, "errors": 0})

        for record in memory.feedback_history:
            fb_type = record.get("user_feedback", "unknown")
            feedback_counts[fb_type] += 1

            recognized = record.get("recognized_intent", "")
            intent_error_rates[recognized]["total"] += 1
            if fb_type in ("negated", "corrected"):
                intent_error_rates[recognized]["errors"] += 1

        error_rates = {}
        for intent, stats in intent_error_rates.items():
            if stats["total"] >= 3:
                error_rates[intent] = round(stats["errors"] / stats["total"], 3)

        return {
            "total": len(memory.feedback_history),
            "confirmed": feedback_counts.get("confirmed", 0),
            "negated": feedback_counts.get("negated", 0),
            "corrected": feedback_counts.get("corrected", 0),
            "error_rates": error_rates
        }

    def get_habit_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取操作习惯建议

        Returns:
            习惯建议列表 (如：生成发货单后经常打印标签)
        """
        memory = self._store.get_memory(user_id)
        if not memory:
            return []

        suggestions = []
        action_sequence = self._analyze_action_sequence(memory)

        for seq in action_sequence:
            if seq["confidence"] >= 0.8 and len(seq["actions"]) >= 2:
                suggestions.append({
                    "type": "action_sequence",
                    "actions": seq["actions"],
                    "confidence": seq["confidence"],
                    "suggestion": f"执行 {seq['actions'][0]} 后主动提示 {seq['actions'][1]}"
                })

        return suggestions

    def _analyze_action_sequence(self, memory: UserMemory) -> List[Dict[str, Any]]:
        """分析操作序列"""
        sequences = defaultdict(lambda: {"count": 0, "first_action": ""})

        for i in range(len(memory.historical_contexts) - 1):
            current = memory.historical_contexts[i]
            next_ctx = memory.historical_contexts[i + 1]

            seq_key = f"{current.get('intent')}->{next_ctx.get('intent')}"
            sequences[seq_key]["count"] += 1
            sequences[seq_key]["first_action"] = current.get("intent")

        result = []
        for seq_key, stats in sequences.items():
            if stats["count"] >= 2:
                actions = seq_key.split("->")
                result.append({
                    "actions": actions,
                    "confidence": min(0.95, stats["count"] * 0.15),
                    "count": stats["count"]
                })

        return result

    def apply_preference_to_slots(
        self,
        user_id: str,
        intent: str,
        slots: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将用户偏好应用到槽位

        Args:
            user_id: 用户ID
            intent: 当前意图
            slots: 当前槽位

        Returns:
            填充后的槽位
        """
        filled_slots = slots.copy()

        if "unit_name" not in filled_slots or not filled_slots["unit_name"]:
            favorite_customer = self.get_preference(user_id, "favorite_customer")
            if favorite_customer:
                filled_slots["unit_name"] = favorite_customer

        if "template" not in filled_slots:
            default_template = self.get_preference(user_id, "default_template")
            if default_template:
                filled_slots["template"] = default_template

        return filled_slots

    def get_memory_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆摘要"""
        memory = self._store.get_memory(user_id)
        if not memory:
            return {"has_memory": False}

        return {
            "has_memory": True,
            "preference_count": len(memory.preferences),
            "action_count": len(memory.frequent_actions),
            "feedback_count": len(memory.feedback_history),
            "last_updated": memory.updated_at,
            "top_intents": [a.get("intent") for a in memory.frequent_actions[:3]]
        }


_user_memory_service: Optional[UserMemoryService] = None


def get_user_memory_service() -> UserMemoryService:
    """获取用户记忆服务单例"""
    global _user_memory_service
    if _user_memory_service is None:
        _user_memory_service = UserMemoryService()
    return _user_memory_service


def reset_user_memory_service() -> None:
    """重置用户记忆服务单例"""
    global _user_memory_service
    _user_memory_service = None
