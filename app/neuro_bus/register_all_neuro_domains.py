"""
在应用启动时注册全部 NeuroDomain，使 Domain 层与总线订阅一致（供迁移与观测）。"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_all_neuro_domains() -> list[str]:
    """
    触发各域单例的 ``get_*_domain()``，完成 DomainRegistry.register。

    Returns:
        当前已注册域名称列表。
    """
    from app.neuro_bus.domains.ai_service_domain import get_ai_service_domain
    from app.neuro_bus.domains.base import get_domain_registry
    from app.neuro_bus.domains.customer_domain import get_customer_domain
    from app.neuro_bus.domains.intent_domain import get_intent_domain
    from app.neuro_bus.domains.inventory_domain import get_inventory_domain
    from app.neuro_bus.domains.ocr_domain import get_ocr_domain
    from app.neuro_bus.domains.order_domain import get_order_domain
    from app.neuro_bus.domains.payment_domain import get_payment_domain
    from app.neuro_bus.domains.print_domain import get_print_domain
    from app.neuro_bus.domains.product_domain import get_product_domain
    from app.neuro_bus.domains.safety_domain import get_safety_domain
    from app.neuro_bus.domains.shipment_domain import get_shipment_domain
    from app.neuro_bus.domains.wechat_domain import get_wechat_domain

    getters = (
        get_intent_domain,
        get_order_domain,
        get_inventory_domain,
        get_product_domain,
        get_customer_domain,
        get_ai_service_domain,
        get_wechat_domain,
        get_print_domain,
        get_ocr_domain,
        get_payment_domain,
        get_safety_domain,
        get_shipment_domain,
    )
    for g in getters:
        try:
            g()
        except Exception as exc:
            logger.warning("NeuroDomain init skipped for %s: %s", g.__name__, exc)

    names = get_domain_registry().list_domains()
    logger.info("NeuroDomain registry: %s (%d)", names, len(names))
    return names
