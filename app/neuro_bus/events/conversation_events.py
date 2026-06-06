"""
Conversation 领域事件定义

包含对话管理的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class ConversationCreatedEvent(NeuroEvent):
    """对话创建事件"""

    event_type: str = "conversation.created"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["conversation_id", "user_id", "channel"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ConversationCreatedEvent 缺少必要字段: {field}")


@dataclass
class ConversationMessageAddedEvent(NeuroEvent):
    """对话消息添加事件"""

    event_type: str = "conversation.message_added"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["conversation_id", "message_id", "sender_type", "content"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ConversationMessageAddedEvent 缺少必要字段: {field}")


@dataclass
class ConversationEndedEvent(NeuroEvent):
    """对话结束事件"""

    event_type: str = "conversation.ended"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["conversation_id", "reason", "duration_seconds"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ConversationEndedEvent 缺少必要字段: {field}")


@dataclass
class ConversationAssignedEvent(NeuroEvent):
    """对话分配事件"""

    event_type: str = "conversation.assigned"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["conversation_id", "assigned_to", "assigned_by"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ConversationAssignedEvent 缺少必要字段: {field}")


@dataclass
class ConversationTaggedEvent(NeuroEvent):
    """对话标签变更事件"""

    event_type: str = "conversation.tagged"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["conversation_id", "tags", "tagged_by"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ConversationTaggedEvent 缺少必要字段: {field}")


@dataclass
class ConversationExportedEvent(NeuroEvent):
    """对话导出事件"""

    event_type: str = "conversation.exported"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["conversation_id", "export_format", "file_path"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ConversationExportedEvent 缺少必要字段: {field}")
