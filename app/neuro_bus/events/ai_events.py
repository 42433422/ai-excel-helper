"""
AI 领域事件定义

包含 AI 对话和意图识别的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class AIIntentRecognizedEvent(NeuroEvent):
    """AI 意图识别事件"""

    event_type: str = "ai.intent_recognized"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["session_id", "user_message", "intent", "confidence"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"AIIntentRecognizedEvent 缺少必要字段: {field}")


@dataclass
class AIResponseGeneratedEvent(NeuroEvent):
    """AI 响应生成事件"""

    event_type: str = "ai.response_generated"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["session_id", "response", "generation_time_ms"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"AIResponseGeneratedEvent 缺少必要字段: {field}")


@dataclass
class AIConversationStartedEvent(NeuroEvent):
    """AI 对话开始事件"""

    event_type: str = "ai.conversation_started"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["session_id", "user_id", "channel"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"AIConversationStartedEvent 缺少必要字段: {field}")


@dataclass
class AIConversationEndedEvent(NeuroEvent):
    """AI 对话结束事件"""

    event_type: str = "ai.conversation_ended"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["session_id", "total_messages", "duration_seconds"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"AIConversationEndedEvent 缺少必要字段: {field}")


@dataclass
class AIFeedbackReceivedEvent(NeuroEvent):
    """AI 反馈接收事件"""

    event_type: str = "ai.feedback_received"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["session_id", "message_id", "feedback_type", "rating"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"AIFeedbackReceivedEvent 缺少必要字段: {field}")


@dataclass
class AIContextUpdatedEvent(NeuroEvent):
    """AI 上下文更新事件"""

    event_type: str = "ai.context_updated"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "session_id" not in self.payload:
            raise ValueError("AIContextUpdatedEvent 缺少必要字段: session_id")
