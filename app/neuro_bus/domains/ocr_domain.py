"""
OCR域（OCRNeuroDomain）

OCR识别事件：请求、识别完成、失败
"""

import logging
from typing import Any

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class OCRNeuroDomain(NeuroDomain):
    """
    OCR神经域

    事件：
    - ocr.requested
    - ocr.completed
    - ocr.failed
    - ocr.batch.completed
    """

    domain_name = "ocr"
    default_channel = DomainChannel.STANDARD

    def __init__(self, bus=None):
        super().__init__(bus)
        self._request_count = 0
        self._success_count = 0
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("ocr.completed", priority=1)
        async def on_completed(event):
            self._success_count += 1
            request_id = event.payload.get("request_id")
            confidence = event.payload.get("confidence")
            logger.debug(f"OCR completed: {request_id}, confidence={confidence}")
            bump_domain_handler_metric("ocr.completed")

    async def initialize(self):
        logger.info("OCRNeuroDomain initialized")

    async def shutdown(self):
        logger.info("OCRNeuroDomain shutdown")

    def emit_ocr_requested(
        self,
        request_id: str,
        image_url: str,
        ocr_type: str,  # "invoice", "id_card", "general"
        user_id: str,
    ) -> bool:
        self._request_count += 1
        return self.emit(
            "ocr.requested",
            priority=EventPriority.NORMAL,
            payload={
                "request_id": request_id,
                "image_url": image_url,
                "ocr_type": ocr_type,
                "user_id": user_id,
            },
        )

    def emit_ocr_completed(
        self,
        request_id: str,
        text: str,
        confidence: float,
        fields: dict[str, str],
    ) -> bool:
        return self.emit(
            "ocr.completed",
            priority=EventPriority.NORMAL,
            payload={
                "request_id": request_id,
                "text": text,
                "confidence": confidence,
                "fields": fields,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        return {
            **base,
            "requests": self._request_count,
            "success": self._success_count,
            "success_rate": self._success_count / max(self._request_count, 1),
        }


_ocr_domain: OCRNeuroDomain | None = None


def get_ocr_domain() -> OCRNeuroDomain:
    global _ocr_domain
    if _ocr_domain is None:
        _ocr_domain = OCRNeuroDomain()
        get_domain_registry().register(_ocr_domain)
    return _ocr_domain
