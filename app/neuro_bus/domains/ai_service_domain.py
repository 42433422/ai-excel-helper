"""
AI服务域（AIServiceNeuroDomain）

AI服务事件：请求、响应、错误、限流
"""

import logging
from typing import Any

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class AIServiceNeuroDomain(NeuroDomain):
    """
    AI服务神经域

    事件：
    - ai.requested
    - ai.completed
    - ai.failed
    - ai.rate_limited
    - ai.model_switched
    """

    domain_name = "ai_service"
    default_channel = DomainChannel.FAST

    def __init__(self, bus=None):
        super().__init__(bus)
        self._request_count = 0
        self._error_count = 0
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("ai.completed", priority=1)
        async def on_completed(event):
            self._request_count += 1
            model = event.payload.get("model")
            latency_ms = event.payload.get("latency_ms")
            logger.debug(f"AI completed: model={model}, latency={latency_ms}ms")
            from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

            bump_domain_handler_metric("ai.completed")

        @self.on("ai.failed", priority=0)
        async def on_failed(event):
            self._error_count += 1
            model = event.payload.get("model")
            error = event.payload.get("error")
            logger.error(f"AI failed: model={model}, error={error}")
            bump_domain_handler_metric("ai.failed")

    async def initialize(self):
        logger.info("AIServiceNeuroDomain initialized")

    async def shutdown(self):
        logger.info("AIServiceNeuroDomain shutdown")

    def emit_ai_requested(
        self,
        request_id: str,
        model: str,
        prompt_length: int,
        user_id: str,
    ) -> bool:
        return self.emit(
            "ai.requested",
            priority=EventPriority.HIGH,
            payload={
                "request_id": request_id,
                "model": model,
                "prompt_length": prompt_length,
                "user_id": user_id,
            },
        )

    def emit_ai_completed(
        self,
        request_id: str,
        model: str,
        latency_ms: float,
        token_count: int,
    ) -> bool:
        return self.emit(
            "ai.completed",
            priority=EventPriority.NORMAL,
            payload={
                "request_id": request_id,
                "model": model,
                "latency_ms": latency_ms,
                "token_count": token_count,
            },
        )

    def emit_ai_failed(
        self,
        request_id: str,
        model: str,
        error: str,
        retryable: bool = False,
    ) -> bool:
        return self.emit(
            "ai.failed",
            priority=EventPriority.NORMAL,
            payload={
                "request_id": request_id,
                "model": model,
                "error": error,
                "retryable": retryable,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        return {
            **base,
            "requests": self._request_count,
            "errors": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
        }


_ai_domain: AIServiceNeuroDomain | None = None


def get_ai_service_domain() -> AIServiceNeuroDomain:
    global _ai_domain
    if _ai_domain is None:
        _ai_domain = AIServiceNeuroDomain()
        get_domain_registry().register(_ai_domain)
    return _ai_domain
