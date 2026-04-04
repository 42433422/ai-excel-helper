"""
基础设施层

此模块包含所有外部依赖和基础设施实现
"""

from .database.database_manager import DatabaseManager
from .session.session_manager import SessionManager
# WeChat is now optional via plugin
from .plugins.wechat_plugin import get_wechat_plugin, is_wechat_available

__all__ = [
    "DatabaseManager",
    "SessionManager",
    "get_wechat_plugin",
    "is_wechat_available",
]
