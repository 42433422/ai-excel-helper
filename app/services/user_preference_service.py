"""
用户偏好服务模块

提供用户偏好设置的业务逻辑。
"""

import logging

from app.db.models import UserPreference
from app.db.session import get_db
from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin

logger = logging.getLogger(__name__)


class UserPreferenceService(NeuroEventPublisherMixin):
    """用户偏好服务类"""

    def __init__(self):
        """初始化用户偏好服务"""
        pass

    def get_preference(self, user_id: str, preference_key: str) -> str | None:
        """
        获取用户偏好

        Args:
            user_id: 用户 ID
            preference_key: 偏好键

        Returns:
            偏好值，如果不存在则返回 None
        """
        with get_db() as db:
            preference = (
                db.query(UserPreference)
                .filter(
                    UserPreference.user_id == user_id,
                    UserPreference.preference_key == preference_key,
                )
                .first()
            )

            return preference.preference_value if preference else None

    def set_preference(self, user_id: str, preference_key: str, preference_value: str) -> bool:
        """
        设置用户偏好

        Args:
            user_id: 用户 ID
            preference_key: 偏好键
            preference_value: 偏好值

        Returns:
            是否设置成功
        """
        with get_db() as db:
            preference = (
                db.query(UserPreference)
                .filter(
                    UserPreference.user_id == user_id,
                    UserPreference.preference_key == preference_key,
                )
                .first()
            )

            if preference:
                preference.preference_value = preference_value
            else:
                preference = UserPreference(
                    user_id=user_id,
                    preference_key=preference_key,
                    preference_value=preference_value,
                )
                db.add(preference)

            db.commit()
            return True

    def get_all_preferences(self, user_id: str) -> dict[str, str]:
        """
        获取用户所有偏好

        Args:
            user_id: 用户 ID

        Returns:
            偏好字典 {key: value}
        """
        with get_db() as db:
            preferences = db.query(UserPreference).filter(UserPreference.user_id == user_id).all()

            return {p.preference_key: p.preference_value for p in preferences}

    def delete_preference(self, user_id: str, preference_key: str) -> bool:
        """
        删除用户偏好

        Args:
            user_id: 用户 ID
            preference_key: 偏好键

        Returns:
            是否删除成功
        """
        with get_db() as db:
            result = (
                db.query(UserPreference)
                .filter(
                    UserPreference.user_id == user_id,
                    UserPreference.preference_key == preference_key,
                )
                .delete()
            )

            db.commit()
            return result > 0


def get_user_preference_service() -> UserPreferenceService:
    """获取用户偏好服务单例"""
    from app.di.registry import get_service_registry

    return get_service_registry().user_preference_service


# NEURO-DDD: 为 Services 层类添加 instrumentation
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(UserPreferenceService, "app.services.user_preference_service")
