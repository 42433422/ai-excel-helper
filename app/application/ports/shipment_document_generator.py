from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ShipmentDocumentGeneratorPort(ABC):
    """发货单文档生成端口（Port）。

    application 只依赖这个抽象，不依赖 legacy 模板实现、文件系统路径等细节。
    """

    @abstractmethod
    def generate(
        self,
        *,
        unit_name: str,
        products: List[Dict[str, Any]],
        date: Optional[str] = None,
        template_name: Optional[str] = None,
        order_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

