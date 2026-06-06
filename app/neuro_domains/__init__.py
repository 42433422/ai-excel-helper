"""
神经域稳定导入面，与 README 中 NeuroDomain 示意图及 ``register_all_neuro_domains`` 一致。

实现代码在 ``app.neuro_bus.domains``；此处仅转发，新业务优先：

    from app.neuro_domains import IntentNeuroDomain, get_intent_domain
"""

from __future__ import annotations

from app.domain.neuro.neuro_uow import NeuroUnitOfWork, neuro_uow_session
from app.domain.neuro.processors.coordinator import (
    ProcessorCoordinator,
    ProcessorType,
    get_processor_coordinator,
)
from app.neuro_bus.domains.ai_service_domain import AIServiceNeuroDomain, get_ai_service_domain
from app.neuro_bus.domains.base import (
    DomainChannel,
    DomainHandler,
    NeuroDomain,
    get_domain_registry,
)
from app.neuro_bus.domains.customer_domain import CustomerNeuroDomain, get_customer_domain
from app.neuro_bus.domains.intent_domain import IntentNeuroDomain, get_intent_domain
from app.neuro_bus.domains.inventory_domain import InventoryNeuroDomain, get_inventory_domain
from app.neuro_bus.domains.ocr_domain import OCRNeuroDomain, get_ocr_domain
from app.neuro_bus.domains.order_domain import OrderNeuroDomain, get_order_domain
from app.neuro_bus.domains.payment_domain import PaymentNeuroDomain, get_payment_domain
from app.neuro_bus.domains.print_domain import PrintNeuroDomain, get_print_domain
from app.neuro_bus.domains.product_domain import ProductNeuroDomain, get_product_domain
from app.neuro_bus.domains.safety_domain import SafetyNeuroDomain, get_safety_domain
from app.neuro_bus.domains.shipment_domain import ShipmentNeuroDomain, get_shipment_domain
from app.neuro_bus.domains.wechat_domain import WechatNeuroDomain, get_wechat_domain

__all__ = [
    "AIServiceNeuroDomain",
    "CustomerNeuroDomain",
    "DomainChannel",
    "DomainHandler",
    "IntentNeuroDomain",
    "InventoryNeuroDomain",
    "NeuroDomain",
    "OCRNeuroDomain",
    "OrderNeuroDomain",
    "PaymentNeuroDomain",
    "PrintNeuroDomain",
    "ProductNeuroDomain",
    "SafetyNeuroDomain",
    "ShipmentNeuroDomain",
    "WechatNeuroDomain",
    "ProcessorCoordinator",
    "ProcessorType",
    "NeuroUnitOfWork",
    "neuro_uow_session",
    "get_ai_service_domain",
    "get_customer_domain",
    "get_domain_registry",
    "get_intent_domain",
    "get_inventory_domain",
    "get_ocr_domain",
    "get_order_domain",
    "get_payment_domain",
    "get_print_domain",
    "get_product_domain",
    "get_safety_domain",
    "get_shipment_domain",
    "get_processor_coordinator",
    "get_wechat_domain",
]
