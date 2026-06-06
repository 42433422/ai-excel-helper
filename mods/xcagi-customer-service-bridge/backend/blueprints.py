"""客服业务页桥接 Mod（里程碑 K）— 页面经 Mod 路由，数据 API 仍走宿主/其它 bridge。"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CUSTOMER_SERVICE_BRIDGE_MOD_ID = "xcagi-customer-service-bridge"


def register_fastapi_routes(app, mod_id: str) -> None:
    from fastapi import APIRouter

    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"customer-service-bridge-{mod_id}"])

    @router.get("/status")
    def status():
        from app.mod_sdk.customer_service_pages_compat import list_customer_service_pages_registry

        return {
            "success": True,
            "data": {
                "ok": True,
                "mod_id": mod_id,
                "registry": list_customer_service_pages_registry(),
            },
        }

    app.include_router(router)
    logger.info("xcagi-customer-service-bridge registered: %s", mod_id)


def mod_init() -> None:
    logger.info("xcagi-customer-service-bridge mod_init (K)")
