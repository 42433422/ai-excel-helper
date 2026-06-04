from __future__ import annotations

from typing import Any

from app.application.ports.wechat_contact_store import WechatContactStorePort


class WechatContactApplicationService:
    def __init__(self, store: WechatContactStorePort):
        self._store = store

    def get_contacts(
        self,
        *,
        keyword: str | None = None,
        contact_type: str | None = None,
        starred_only: bool = False,
        limit: int = 100,
        default_starred_when_all: bool = True,
    ) -> list[dict[str, Any]]:
        return self._store.list_contacts(
            keyword=keyword,
            contact_type=contact_type,
            starred_only=starred_only,
            limit=limit,
            default_starred_when_all=default_starred_when_all,
        )

    def get_contact_by_id(self, contact_id: int) -> dict[str, Any] | None:
        return self._store.get_contact(contact_id)

    def add_contact(self, **kwargs) -> dict[str, Any]:
        return self._store.add_contact(**kwargs)

    def update_contact(self, contact_id: int, **kwargs) -> dict[str, Any]:
        return self._store.update_contact(contact_id, kwargs)

    def delete_contact(self, contact_id: int) -> dict[str, Any]:
        return self._store.delete_contact(contact_id)

    def unstar_all(self) -> dict[str, Any]:
        return self._store.unstar_all()

    def get_contact_context(self, contact_id: int) -> list[dict[str, Any]]:
        return self._store.get_context(contact_id)

    def save_contact_context(
        self, contact_id: int, wechat_id: str, messages: list[dict[str, Any]]
    ) -> bool:
        return self._store.save_context(contact_id, wechat_id, messages)


from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(WechatContactApplicationService)


def get_wechat_contact_app_service() -> WechatContactApplicationService:
    """获取微信联系人服务单例"""
    from app.di.registry import get_service_registry

    return get_service_registry().wechat_contact_application_service
