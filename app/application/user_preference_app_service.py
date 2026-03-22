"""
用户偏好应用服务

此模块已迁移到 app/application/
"""

from datetime import datetime
from typing import Any, Dict, Optional


class UserPreferenceApplicationService:
    """用户偏好应用服务"""

    def __init__(self):
        pass

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        try:
            from app.utils.user_memory import get_user_memory_service
            memory_service = get_user_memory_service()
            return memory_service.get_preference(user_id, key, default)
        except Exception:
            return default

    def set_preference(self, user_id: str, key: str, value: Any) -> bool:
        try:
            from app.utils.user_memory import get_user_memory_service
            memory_service = get_user_memory_service()
            memory_service.add_preference(user_id, key, value)
            return True
        except Exception:
            return False

    def get_all_preferences(self, user_id: str) -> Dict[str, Any]:
        try:
            from app.utils.user_memory import get_user_memory_service
            memory_service = get_user_memory_service()
            return memory_service.get_all_preferences(user_id)
        except Exception:
            return {}


_user_preference_app_service: Optional[UserPreferenceApplicationService] = None


def get_user_preference_app_service() -> UserPreferenceApplicationService:
    global _user_preference_app_service
    if _user_preference_app_service is None:
        _user_preference_app_service = UserPreferenceApplicationService()
    return _user_preference_app_service
