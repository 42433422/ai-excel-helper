"""
Neuro 迁移与分层观测路由（不改变业务契约，仅用于健康检查 / CI / 排障）。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/neuro", tags=["neuro-migration"])


@router.get("/migration-smoke")
async def neuro_migration_smoke() -> dict[str, Any]:
    """
    返回 Neuro 栈与 Domain 注册、反射弧、Application 挂钩等自检信息。
    """
    from app.neuro_bus.bus import get_neuro_bus
    from app.neuro_bus.domains.base import get_domain_registry
    from app.neuro_bus.integrations.intent_integration import (
        is_neuro_stack_enabled,
        try_neuro_reflex_intent,
    )

    enabled = is_neuro_stack_enabled()
    bus = get_neuro_bus()
    domains: list[str] = []
    reflex_hit: dict[str, Any] | None = None
    if enabled:
        domains = list(get_domain_registry().list_domains())
        reflex_hit = try_neuro_reflex_intent("你好", "migration-smoke")

    return {
        "neuro_stack_enabled": enabled,
        "bus_running": bool(bus.is_running),
        "registered_domains": domains,
        "registered_domain_count": len(domains),
        "expected_domain_count": 11,
        "reflex_greeting_hit": bool(reflex_hit and reflex_hit.get("is_greeting")),
        "application_layer_hooks": [
            "AIChatApplicationService.process_chat → neuro_notify_chat_received / neuro_notify_chat_completed",
            "ConversationApplicationService.save_message → neuro_notify_conversation_message_saved",
        ],
        "services_layer_hooks": [
            "AIConversationService._recognize_intent → intent_integration + neuro_notify_intent_resolved",
            "Optional: neuro_notify_ai_model_roundtrip（主模型推理完成后在 Services 内手动调用）",
        ],
        "related_http_routes": [
            "/api/neuro/migration-smoke",
            "/api/neurobus/health",
            "/api/neurobus/stats",
            "/api/health (includes neuro summary when enabled)",
        ],
        "trace_environment_variables": [
            "XCAGI_NEURO_HTTP_TRACE",
            "XCAGI_NEURO_HTTP_SAMPLE",
            "XCAGI_NEURO_HTTP_BODY_MAX",
            "XCAGI_NEURO_APP_SAMPLE",
            "XCAGI_NEURO_SERVICE_TRACE",
            "XCAGI_NEURO_DOMAIN_METRICS",
        ],
        "operations_doc": "NEURO_OPERATIONS.md",
    }
