"""NeuroBus 桥接 Mod（M/M+/N）— 诊断 API 门面 + 领域 handler 注册编排，总线仍在宿主。"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DOMAIN_IDS = [
    "intent",
    "order",
    "inventory",
    "product",
    "customer",
    "ai_service",
    "wechat",
    "print",
    "ocr",
    "payment",
    "safety",
    "shipment",
]


def register_fastapi_routes(app, mod_id: str) -> None:
    from fastapi import APIRouter, Body

    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"neuro-bus-bridge-{mod_id}"])

    @router.get("/status")
    def status():
        from app.mod_sdk.neuro_bus_compat import list_neuro_bus_facade_registry

        return {
            "success": True,
            "data": {**list_neuro_bus_facade_registry(), "mod_id": mod_id, "domains": DOMAIN_IDS},
        }

    @router.get("/registry")
    def registry():
        from app.mod_sdk.neuro_bus_compat import list_neuro_bus_facade_registry

        return {"success": True, "data": list_neuro_bus_facade_registry()}

    @router.get("/handlers/registry")
    def handlers_registry():
        from app.mod_sdk.neuro_bus_handler_registry import list_neuro_bus_handler_registry

        return {"success": True, "data": list_neuro_bus_handler_registry(), "source": f"mod:{mod_id}"}

    @router.get("/handlers/catalog")
    def handlers_catalog():
        from app.infrastructure.mods.mod_manager import import_mod_backend_py

        mod = import_mod_backend_py(
            str(Path(__file__).resolve().parent.parent),
            mod_id,
            "handler_providers",
        )
        return {
            "success": True,
            "data": {
                "catalog": mod.load_handler_catalog(),
                "summary": mod.summarize_handler_catalog(),
            },
            "source": f"mod:{mod_id}",
        }

    @router.get("/neurobus/health")
    async def mod_neurobus_health():
        from app.neuro_bus.integrations.fastapi_integration import get_neurobus_health

        return {"success": True, "data": get_neurobus_health(), "source": f"mod:{mod_id}"}

    @router.get("/neurobus/stats")
    async def mod_neurobus_stats():
        from app.neuro_bus.bus import get_neuro_bus

        bus = get_neuro_bus()
        stats = bus.get_stats() if hasattr(bus, "get_stats") else {}
        return {"success": True, "data": stats, "source": f"mod:{mod_id}"}

    @router.post("/events/publish")
    async def mod_publish_event(body: dict = Body(default_factory=dict)):
        """里程碑 M+：经 Mod 门面发布领域事件（委托宿主 NeuroBus）。"""
        payload_in = body if isinstance(body, dict) else {}
        event_type = str(payload_in.get("event_type") or "").strip()
        domain = str(payload_in.get("domain") or "global").strip() or "global"
        event_payload = payload_in.get("payload")
        if not isinstance(event_payload, dict):
            event_payload = {}
        if not event_type:
            return {"success": False, "message": "event_type_required"}
        from app.neuro_bus.application_neuro_bridge import publish_neuro_event

        ok = publish_neuro_event(event_type, event_payload, domain=domain)
        return {
            "success": True,
            "data": {
                "published": bool(ok),
                "event_type": event_type,
                "domain": domain,
                "source": f"mod:{mod_id}",
                "execution_path": "mod_event_facade",
            },
        }

    app.include_router(router)
    logger.info("xcagi-neuro-bus-bridge registered (phase M/N): %s", mod_id)


def mod_init(app=None, mod_id: str | None = None):
    logger.info("xcagi-neuro-bus-bridge mod_init (phase N handlers catalog)")
