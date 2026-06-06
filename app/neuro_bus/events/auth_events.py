"""
Auth 领域事件定义

包含认证授权的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class UserLoginEvent(NeuroEvent):
    """用户登录事件"""

    event_type: str = "auth.user_login"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["user_id", "login_method", "ip_address"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"UserLoginEvent 缺少必要字段: {field}")


@dataclass
class UserLogoutEvent(NeuroEvent):
    """用户登出事件"""

    event_type: str = "auth.user_logout"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "user_id" not in self.payload:
            raise ValueError("UserLogoutEvent 缺少必要字段: user_id")


@dataclass
class UserRegisteredEvent(NeuroEvent):
    """用户注册事件"""

    event_type: str = "auth.user_registered"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["user_id", "username", "registration_source"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"UserRegisteredEvent 缺少必要字段: {field}")


@dataclass
class UserPasswordChangedEvent(NeuroEvent):
    """用户密码变更事件"""

    event_type: str = "auth.password_changed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        if "user_id" not in self.payload:
            raise ValueError("UserPasswordChangedEvent 缺少必要字段: user_id")


@dataclass
class UserPermissionGrantedEvent(NeuroEvent):
    """用户权限授予事件"""

    event_type: str = "auth.permission_granted"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["user_id", "permission", "granted_by"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"UserPermissionGrantedEvent 缺少必要字段: {field}")


@dataclass
class UserPermissionRevokedEvent(NeuroEvent):
    """用户权限撤销事件"""

    event_type: str = "auth.permission_revoked"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["user_id", "permission", "revoked_by"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"UserPermissionRevokedEvent 缺少必要字段: {field}")


@dataclass
class LoginFailedEvent(NeuroEvent):
    """登录失败事件"""

    event_type: str = "auth.login_failed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["username", "reason", "ip_address"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"LoginFailedEvent 缺少必要字段: {field}")


@dataclass
class TokenRefreshedEvent(NeuroEvent):
    """Token 刷新事件"""

    event_type: str = "auth.token_refreshed"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        if "user_id" not in self.payload:
            raise ValueError("TokenRefreshedEvent 缺少必要字段: user_id")
