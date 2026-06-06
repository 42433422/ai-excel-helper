from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ShipmentRecordStorePort(ABC):
    """出货记录写入端口（Port）。

    目标：统一所有写入都以 purchase_units 的规范单位名/ID 为准。
    """

    @abstractmethod
    def record_document_generation(
        self,
        *,
        unit_name: str,
        unit_id: int | None,
        products: list[dict[str, Any]],
        document_result: dict[str, Any],
        raw_text: str = "",
    ) -> dict[str, Any]:
        """记录一次发货单生成对应的出货记录。"""
        raise NotImplementedError
