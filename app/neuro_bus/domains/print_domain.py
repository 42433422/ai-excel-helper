"""
打印域（PrintNeuroDomain）

打印服务事件：任务提交、开始、完成、失败
"""

import logging
from typing import Any

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class PrintNeuroDomain(NeuroDomain):
    """
    打印神经域

    事件：
    - print.job.submitted
    - print.job.started
    - print.job.completed
    - print.job.failed
    - print.printer.error
    """

    domain_name = "print"
    default_channel = DomainChannel.STANDARD

    def __init__(self, bus=None):
        super().__init__(bus)
        self._active_jobs = 0
        self._completed_jobs = 0
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("print.job.started", priority=2)
        async def on_started(event):
            self._active_jobs += 1
            job_id = event.payload.get("job_id")
            logger.info(f"Print started: {job_id}")
            bump_domain_handler_metric("print.job.started")

        @self.on("print.job.completed", priority=2)
        async def on_completed(event):
            self._active_jobs -= 1
            self._completed_jobs += 1
            job_id = event.payload.get("job_id")
            logger.info(f"Print completed: {job_id}")
            bump_domain_handler_metric("print.job.completed")

    async def initialize(self):
        logger.info("PrintNeuroDomain initialized")

    async def shutdown(self):
        logger.info("PrintNeuroDomain shutdown")

    def emit_job_submitted(
        self,
        job_id: str,
        document_name: str,
        printer_id: str,
        copies: int = 1,
    ) -> bool:
        return self.emit(
            "print.job.submitted",
            priority=EventPriority.NORMAL,
            payload={
                "job_id": job_id,
                "document_name": document_name,
                "printer_id": printer_id,
                "copies": copies,
            },
        )

    def emit_job_completed(
        self,
        job_id: str,
        pages_printed: int,
        duration_ms: float,
    ) -> bool:
        return self.emit(
            "print.job.completed",
            priority=EventPriority.NORMAL,
            payload={
                "job_id": job_id,
                "pages_printed": pages_printed,
                "duration_ms": duration_ms,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        return {
            **base,
            "active_jobs": self._active_jobs,
            "completed_jobs": self._completed_jobs,
        }


_print_domain: PrintNeuroDomain | None = None


def get_print_domain() -> PrintNeuroDomain:
    global _print_domain
    if _print_domain is None:
        _print_domain = PrintNeuroDomain()
        get_domain_registry().register(_print_domain)
    return _print_domain
