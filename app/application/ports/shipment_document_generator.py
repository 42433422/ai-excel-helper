from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ShipmentDocumentGeneratorPort(ABC):
    """发货单文档生成端口（Port）。

    application 只依赖这个抽象，不依赖 legacy 模板实现、文件系统路径等细节。
    """

    @abstractmethod
    def generate(
        self,
        *,
        unit_name: str,
        products: list[dict[str, Any]],
        date: str | None = None,
        template_name: str | None = None,
        order_number: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
