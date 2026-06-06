"""
PrinterService Domain Event Handlers (V2)

Auto-generated event handlers for print domain
"""

import logging
from typing import Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import NeuroEvent
from app.neuro_bus.events.print_events import (
    LabelPrintRequestEvent,
    PrintJobCompletedEvent,
    PrintJobSubmittedEvent,
)

logger = logging.getLogger(__name__)


class PrinterServiceDomainHandlers:
    """PrinterService 领域事件处理器"""

    def __init__(self):
        self.bus = get_neuro_bus()

    def register(self):
        """注册所有事件处理器"""
        self.bus.subscribe("print.job_submitted", self.handle_job_submitted)
        self.bus.subscribe("print.job_completed", self.handle_job_completed)
        self.bus.subscribe("print.label_requested", self.handle_label_requested)
        logger.info("[PrinterServiceDomain] 已注册 {len(self.bus.subscribers)} 个事件处理器")

    async def handle_job_submitted(self, event: NeuroEvent) -> dict[str, Any]:
        """处理 job_submitted 事件"""
        logger.info(f"[PrinterServiceDomain] 处理 job_submitted: {event.payload}")
        if isinstance(event, PrintJobSubmittedEvent):
            logger.info(f"[PrinterServiceDomain] Job ID: {event.payload.get('job_id')}")
        return {"success": True, "event_type": "print.job_submitted"}

    async def handle_job_completed(self, event: NeuroEvent) -> dict[str, Any]:
        """处理 job_completed 事件"""
        logger.info(f"[PrinterServiceDomain] 处理 job_completed: {event.payload}")
        if isinstance(event, PrintJobCompletedEvent):
            logger.info(f"[PrinterServiceDomain] Pages: {event.payload.get('pages_printed')}")
        return {"success": True, "event_type": "print.job_completed"}

    async def handle_label_requested(self, event: NeuroEvent) -> dict[str, Any]:
        """处理 label_requested 事件"""
        logger.info(f"[PrinterServiceDomain] 处理 label_requested: {event.payload}")
        if isinstance(event, LabelPrintRequestEvent):
            logger.info(f"[PrinterServiceDomain] Label: {event.payload.get('label_type')}")
        return {"success": True, "event_type": "print.label_requested"}


# 全局处理器实例
_handlers: PrinterServiceDomainHandlers = None


def get_print_handlers() -> PrinterServiceDomainHandlers:
    """获取领域处理器单例"""
    global _handlers
    if _handlers is None:
        _handlers = PrinterServiceDomainHandlers()
    return _handlers


def register_print_domain_handlers(bus):
    """注册所有 Print 领域事件处理器到 NeuroBus"""
    handlers = get_print_handlers()
    handlers.register()
    logger.info("[PrintDomain] 所有事件处理器已注册")
