from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WechatContactStorePort(ABC):
    """微信联系人库端口（Port）。单一来源：只认主库 wechat_contacts / wechat_contact_context。"""

    @abstractmethod
    def list_contacts(
        self,
        *,
        keyword: str | None = None,
        contact_type: str | None = None,
        starred_only: bool = False,
        limit: int = 100,
        default_starred_when_all: bool = True,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_contact(self, contact_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def add_contact(
        self,
        *,
        contact_name: str,
        remark: str = "",
        wechat_id: str = "",
        contact_type: str = "contact",
        is_starred: bool = True,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_contact(self, contact_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete_contact(self, contact_id: int) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def unstar_all(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_context(self, contact_id: int) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_context(self, contact_id: int, wechat_id: str, messages: list[dict[str, Any]]) -> bool:
        raise NotImplementedError
