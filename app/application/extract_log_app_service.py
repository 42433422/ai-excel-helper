"""
提取日志应用服务

负责提取日志管理相关的用例编排
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.application.ports.extract_log_store import ExtractLogStorePort


class ExtractLogApplicationService:
    """提取日志应用服务 - 负责提取日志相关的用例编排"""

    def __init__(
        self,
        store: Optional["ExtractLogStorePort"] = None,
    ):
        if store is None:
            from app.infrastructure.persistence.extract_log_store_impl import (
                SQLAlchemyExtractLogStore,
            )
            store = SQLAlchemyExtractLogStore()
        self._store = store

    def get_extract_logs(
        self,
        page: int = 1,
        per_page: int = 20,
        unit_name: Optional[str] = None
    ) -> Dict[str, Any]:
        return self._store.find_all(
            page=page,
            per_page=per_page,
            unit_name=unit_name
        )

    def get_extract_log(self, log_id: int) -> Dict[str, Any]:
        result = self._store.find_by_id(log_id)
        if result is None:
            return {
                "success": False,
                "message": "日志不存在"
            }
        return {
            "success": True,
            "data": result
        }

    def create_extract_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._store.create(log_data)

    def delete_extract_log(self, log_id: int) -> Dict[str, Any]:
        return self._store.delete(log_id)

    def clear_old_logs(self, days: int = 30) -> Dict[str, Any]:
        return self._store.clear_old(days=days)


_extract_log_app_service: Optional[ExtractLogApplicationService] = None


def get_extract_log_app_service() -> "ExtractLogApplicationService":
    """获取提取日志应用服务单例"""
    global _extract_log_app_service
    if _extract_log_app_service is None:
        _extract_log_app_service = ExtractLogApplicationService()
    return _extract_log_app_service


def get_extract_log_application_service() -> "ExtractLogApplicationService":
    """获取提取日志应用服务单例 (别名)"""
    return get_extract_log_app_service()


def init_extract_log_application_service(
    store: "ExtractLogStorePort",
) -> "ExtractLogApplicationService":
    """初始化提取日志应用服务 (用于依赖注入)"""
    global _extract_log_app_service
    _extract_log_app_service = ExtractLogApplicationService(store=store)
    return _extract_log_app_service


def init_extract_log_app_service(
    store: "ExtractLogStorePort",
) -> "ExtractLogApplicationService":
    """初始化提取日志应用服务 (用于依赖注入) (别名)"""
    return init_extract_log_application_service(store)
