"""
WeChat 领域事件定义

包含微信相关功能的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class WeChatMessageReceivedEvent(NeuroEvent):
    """微信消息接收事件"""

    event_type: str = "wechat.message_received"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["message_id", "from_user", "message_type", "content"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"WeChatMessageReceivedEvent 缺少必要字段: {field}")


@dataclass
class WeChatMessageSentEvent(NeuroEvent):
    """微信消息发送事件"""

    event_type: str = "wechat.message_sent"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["message_id", "to_user", "message_type", "status"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"WeChatMessageSentEvent 缺少必要字段: {field}")


@dataclass
class WeChatContactAddedEvent(NeuroEvent):
    """微信联系人添加事件"""

    event_type: str = "wechat.contact_added"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["contact_id", "contact_name", "source"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"WeChatContactAddedEvent 缺少必要字段: {field}")


@dataclass
class WeChatContactUpdatedEvent(NeuroEvent):
    """微信联系人更新事件"""

    event_type: str = "wechat.contact_updated"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        if "contact_id" not in self.payload:
            raise ValueError("WeChatContactUpdatedEvent 缺少必要字段: contact_id")


@dataclass
class WeChatTaskCreatedEvent(NeuroEvent):
    """微信任务创建事件"""

    event_type: str = "wechat.task_created"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["task_id", "task_type", "target_contacts", "content"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"WeChatTaskCreatedEvent 缺少必要字段: {field}")


@dataclass
class WeChatTaskCompletedEvent(NeuroEvent):
    """微信任务完成事件"""

    event_type: str = "wechat.task_completed"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["task_id", "success_count", "failed_count"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"WeChatTaskCompletedEvent 缺少必要字段: {field}")


@dataclass
class WeChatLoginStatusChangedEvent(NeuroEvent):
    """微信登录状态变更事件"""

    event_type: str = "wechat.login_status_changed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["account_id", "old_status", "new_status"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"WeChatLoginStatusChangedEvent 缺少必要字段: {field}")
