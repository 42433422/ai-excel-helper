from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.application.ports.wechat_contact_store import WechatContactStorePort


class WechatContactApplicationService:
    def __init__(self, store: WechatContactStorePort):
        self._store = store

    def get_contacts(
        self,
        *,
        keyword: Optional[str] = None,
        contact_type: Optional[str] = None,
        starred_only: bool = False,
        limit: int = 100,
        default_starred_when_all: bool = True,
    ) -> List[Dict[str, Any]]:
        return self._store.list_contacts(
            keyword=keyword,
            contact_type=contact_type,
            starred_only=starred_only,
            limit=limit,
            default_starred_when_all=default_starred_when_all,
        )

    def get_contact_by_id(self, contact_id: int) -> Optional[Dict[str, Any]]:
        return self._store.get_contact(contact_id)

    def add_contact(self, **kwargs) -> Dict[str, Any]:
        return self._store.add_contact(**kwargs)

    def update_contact(self, contact_id: int, **kwargs) -> Dict[str, Any]:
        return self._store.update_contact(contact_id, kwargs)

    def delete_contact(self, contact_id: int) -> Dict[str, Any]:
        return self._store.delete_contact(contact_id)

    def unstar_all(self) -> Dict[str, Any]:
        return self._store.unstar_all()

    def get_contact_context(self, contact_id: int) -> List[Dict[str, Any]]:
        return self._store.get_context(contact_id)

    def save_contact_context(self, contact_id: int, wechat_id: str, messages: List[Dict[str, Any]]) -> bool:
        return self._store.save_context(contact_id, wechat_id, messages)


_wechat_contact_app_service_instance = None
_default_store_instance = None


def get_wechat_contact_app_service() -> WechatContactApplicationService:
    """获取微信联系人服务单例"""
    global _wechat_contact_app_service_instance, _default_store_instance
    if _wechat_contact_app_service_instance is None:
        from app.infrastructure.persistence.wechat_contact_store_impl import (
            SQLAlchemyWechatContactStore,
        )
        if _default_store_instance is None:
            _default_store_instance = SQLAlchemyWechatContactStore()
        _wechat_contact_app_service_instance = WechatContactApplicationService(_default_store_instance)
    return _wechat_contact_app_service_instance

