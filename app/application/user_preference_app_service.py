"""
用户偏好应用服务

此模块已迁移到 app/application/
"""

from typing import Any


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

    def get_all_preferences(self, user_id: str) -> dict[str, Any]:
        try:
            from app.utils.user_memory import get_user_memory_service

            memory_service = get_user_memory_service()
            return memory_service.get_all_preferences(user_id)
        except Exception:
            return {}


from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(UserPreferenceApplicationService)

_user_preference_app_service: UserPreferenceApplicationService | None = None


def get_user_preference_app_service() -> UserPreferenceApplicationService:
    global _user_preference_app_service
    if _user_preference_app_service is None:
        _user_preference_app_service = UserPreferenceApplicationService()
    return _user_preference_app_service
