"""
OCRService Domain Event Handlers (V2)

Auto-generated event handlers for ocr domain
"""

import logging
from typing import Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import NeuroEvent
from app.neuro_bus.events.ocr_events import (
    OCRBatchProcessingCompletedEvent,
    OCRTaskCompletedEvent,
    OCRTaskSubmittedEvent,
)

logger = logging.getLogger(__name__)


class OCRServiceDomainHandlers:
    """OCRService 领域事件处理器"""

    def __init__(self):
        self.bus = get_neuro_bus()

    def register(self):
        """注册所有事件处理器"""
        self.bus.subscribe("ocr.task_submitted", self.handle_task_submitted)
        self.bus.subscribe("ocr.task_completed", self.handle_task_completed)
        self.bus.subscribe("ocr.batch_started", self.handle_batch_started)
        logger.info("[OCRServiceDomain] 已注册 {len(self.bus.subscribers)} 个事件处理器")

    async def handle_task_submitted(self, event: NeuroEvent) -> dict[str, Any]:
        """处理 task_submitted 事件"""
        logger.info(f"[OCRServiceDomain] 处理 task_submitted: {event.payload}")
        if isinstance(event, OCRTaskSubmittedEvent):
            logger.info(f"[OCRServiceDomain] Task ID: {event.payload.get('task_id')}")
        return {"success": True, "event_type": "ocr.task_submitted"}

    async def handle_task_completed(self, event: NeuroEvent) -> dict[str, Any]:
        """处理 task_completed 事件"""
        logger.info(f"[OCRServiceDomain] 处理 task_completed: {event.payload}")
        if isinstance(event, OCRTaskCompletedEvent):
            logger.info(f"[OCRServiceDomain] Result: {event.payload.get('result')}")
        return {"success": True, "event_type": "ocr.task_completed"}

    async def handle_batch_started(self, event: NeuroEvent) -> dict[str, Any]:
        """处理 batch_started 事件"""
        logger.info(f"[OCRServiceDomain] 处理 batch_started: {event.payload}")
        if isinstance(event, OCRBatchProcessingCompletedEvent):
            logger.info(f"[OCRServiceDomain] Batch: {event.payload.get('batch_id')}")
        return {"success": True, "event_type": "ocr.batch_started"}


# 全局处理器实例
_handlers: OCRServiceDomainHandlers = None


def get_ocr_handlers() -> OCRServiceDomainHandlers:
    """获取领域处理器单例"""
    global _handlers
    if _handlers is None:
        _handlers = OCRServiceDomainHandlers()
    return _handlers


def register_ocr_domain_handlers(bus):
    """注册所有 OCR 领域事件处理器到 NeuroBus"""
    handlers = get_ocr_handlers()
    handlers.register()
    logger.info("[OCRDomain] 所有事件处理器已注册")
