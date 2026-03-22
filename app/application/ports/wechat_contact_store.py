from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class WechatContactStorePort(ABC):
    """微信联系人库端口（Port）。单一来源：只认主库 wechat_contacts / wechat_contact_context。"""

    @abstractmethod
    def list_contacts(
        self,
        *,
        keyword: Optional[str] = None,
        contact_type: Optional[str] = None,
        starred_only: bool = False,
        limit: int = 100,
        default_starred_when_all: bool = True,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_contact(self, contact_id: int) -> Optional[Dict[str, Any]]:
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
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_contact(self, contact_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete_contact(self, contact_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def unstar_all(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_context(self, contact_id: int) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_context(self, contact_id: int, wechat_id: str, messages: List[Dict[str, Any]]) -> bool:
        raise NotImplementedError

