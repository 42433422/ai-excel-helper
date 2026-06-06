"""模型付费桥接 Mod（里程碑 J）— 全量门面路由，委托宿主 model_payment 实现。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Header, Query, Request

logger = logging.getLogger(__name__)

HOST_PREFIXES = ["/api/model-payment"]


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"model-payment-bridge-{mod_id}"])

    @router.get("/status")
    def status():
        from app.mod_sdk.model_payment_compat import list_model_payment_facade_registry

        return {
            "success": True,
            "data": {**list_model_payment_facade_registry(), "mod_id": mod_id, "phase": "J"},
        }

    @router.get("/registry")
    def registry():
        from app.mod_sdk.model_payment_compat import list_model_payment_facade_registry

        return {"success": True, "data": list_model_payment_facade_registry()}

    @router.get("/model-payment/plans")
    def mod_get_plans():
        from app.fastapi_routes.model_payment import get_plans

        return get_plans()

    @router.post("/model-payment/checkout")
    def mod_checkout(
        body: dict[str, Any] = Body(default_factory=dict),
        user_agent: str | None = Header(default=None),
    ):
        from app.fastapi_routes.model_payment import checkout

        return checkout(body, user_agent)

    @router.post("/model-payment/notify/alipay")
    async def mod_alipay_notify(request: Request):
        from app.fastapi_routes.model_payment import alipay_trade_notify

        return await alipay_trade_notify(request)

    @router.get("/model-payment/diagnostics")
    def mod_diagnostics():
        from app.fastapi_routes.model_payment import diagnostics

        return diagnostics()

    @router.get("/model-payment/entitlements")
    def mod_entitlements():
        from app.fastapi_routes.model_payment import entitlements

        return entitlements()

    @router.get("/model-payment/query/{out_trade_no}")
    def mod_query_trade(out_trade_no: str):
        from app.fastapi_routes.model_payment import query_trade

        return query_trade(out_trade_no)

    @router.post("/model-payment/refund")
    def mod_refund(body: dict[str, Any] = Body(default_factory=dict)):
        from app.fastapi_routes.model_payment import refund_trade

        return refund_trade(body)

    @router.post("/model-payment/close")
    def mod_close(body: dict[str, Any] = Body(default_factory=dict)):
        from app.fastapi_routes.model_payment import close_trade

        return close_trade(body)

    @router.get("/model-payment/refund/query")
    def mod_refund_query(out_trade_no: str, out_request_no: str | None = None):
        from app.fastapi_routes.model_payment import refund_query

        return refund_query(out_trade_no, out_request_no)

    app.include_router(router)


def mod_init():
    logger.info("xcagi-model-payment-bridge initialized (phase J)")
