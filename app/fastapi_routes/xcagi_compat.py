"""
XCAGI 前端兼容 API（FastAPI APIRouter）— 聚合入口。

子路由由 ``domains/<domain>/`` 实现；本文件仅聚合 router，无 legacy shim 依赖。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.fastapi_routes.domains.conversation.compat_extra import router as conversation_extra_router
from app.fastapi_routes.domains.conversation.compat_routes import router as chat_router
from app.fastapi_routes.domains.customer.routes import router as customer_router
from app.fastapi_routes.domains.misc.routes import router as misc_router
from app.fastapi_routes.domains.product.compat_routes import router as product_compat_router
from app.fastapi_routes.domains.product.routes import router as product_legacy_router
from app.fastapi_routes.domains.template.routes import router as template_router
from app.fastapi_routes.domains.wechat.compat_routes import router as wechat_compat_router
from app.fastapi_routes.domains.wechat.routes import router as wechat_legacy_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["xcagi-compat"])

_wechat = APIRouter()
_wechat.include_router(wechat_legacy_router)
_wechat.include_router(wechat_compat_router)
router.include_router(_wechat)

_product = APIRouter()
_product.include_router(product_legacy_router)
_product.include_router(product_compat_router)
router.include_router(_product)

router.include_router(customer_router)
router.include_router(chat_router)
router.include_router(conversation_extra_router)
router.include_router(template_router)
router.include_router(misc_router)


def _register_router_events():
    try:
        from app.neuro_bus.bus import get_neuro_bus

        bus = get_neuro_bus()
        logger.info(
            "[XCAGICompat] 路由已注册到 NeuroBus，当前订阅者: %s",
            len(bus.subscribers),
        )
    except Exception as e:
        logger.debug("[XCAGICompat] NeuroBus 注册跳过: %s", e)


_register_router_events()
