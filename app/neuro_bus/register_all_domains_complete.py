"""
注册所有 Neuro 领域事件处理器（完整版）

一次性注册所有 12 个领域的事件处理器：
1. product - 产品领域
2. shipment - 发货单领域
3. order - 订单领域
4. customer - 客户领域
5. inventory - 库存领域
6. payment - 支付领域
7. ocr - OCR领域
8. wechat - 微信领域
9. print - 打印领域
10. ai - AI领域
11. auth - 认证领域
12. material - 物料领域
"""

import asyncio
import logging

from app.neuro_bus.bus import NeuroBus, get_neuro_bus

logger = logging.getLogger(__name__)


async def register_domain_handlers_only(bus: NeuroBus | None = None) -> None:
    """
    注册各 BC 的 ``*_domain_handlers``（不调用 register_all_neuro_domains）。
    与 ``register_runtime.register_neuro_runtime`` 配合：先 NeuroDomain 类，再本函数。
    """
    if bus is None:
        bus = get_neuro_bus()

    logger.info("[NeuroDomainRegistration] 开始注册领域事件处理器（handler 模块）")

    # 1. Product 领域
    try:
        from app.neuro_bus.domains.product_domain_handlers import register_product_domain_handlers

        register_product_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Product 领域处理器注册完成")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Product 领域注册失败: {e}")

    # 3. Shipment 领域
    try:
        from app.neuro_bus.domains.shipment_domain_handlers import register_shipment_domain_handlers

        register_shipment_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Shipment 领域处理器注册完成")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Shipment 领域注册失败: {e}")

    # 4. Order 领域
    try:
        # 如果存在 order 处理器，则注册
        from app.neuro_bus.domains.order_domain_handlers import register_order_domain_handlers

        register_order_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Order 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Order 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Order 领域注册失败: {e}")

    # 5. Customer 领域
    try:
        from app.neuro_bus.domains.customer_domain_handlers import register_customer_domain_handlers

        register_customer_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Customer 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Customer 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Customer 领域注册失败: {e}")

    # 6. Inventory 领域
    try:
        from app.neuro_bus.domains.inventory_domain_handlers import (
            register_inventory_domain_handlers,
        )

        register_inventory_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Inventory 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Inventory 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Inventory 领域注册失败: {e}")

    # 7. Payment 领域
    try:
        from app.neuro_bus.domains.payment_domain_handlers import register_payment_domain_handlers

        register_payment_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Payment 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Payment 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Payment 领域注册失败: {e}")

    # 8. OCR 领域
    try:
        from app.neuro_bus.domains.ocr_domain_handlers import register_ocr_domain_handlers

        register_ocr_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] OCR 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] OCR 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] OCR 领域注册失败: {e}")

    # 9. WeChat 领域
    try:
        from app.neuro_bus.domains.wechat_domain_handlers import register_wechat_domain_handlers

        register_wechat_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] WeChat 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] WeChat 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] WeChat 领域注册失败: {e}")

    # 10. Print 领域
    try:
        from app.neuro_bus.domains.print_domain_handlers import register_print_domain_handlers

        register_print_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Print 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Print 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Print 领域注册失败: {e}")

    # 11. AI 领域
    try:
        from app.neuro_bus.domains.ai_domain_handlers import register_ai_domain_handlers

        register_ai_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] AI 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] AI 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] AI 领域注册失败: {e}")

    # 12. Auth 领域
    try:
        from app.neuro_bus.domains.auth_domain_handlers import register_auth_domain_handlers

        register_auth_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Auth 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Auth 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Auth 领域注册失败: {e}")

    # 13. Material 领域
    try:
        from app.neuro_bus.domains.material_domain_handlers import register_material_domain_handlers

        register_material_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Material 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Material 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Material 领域注册失败: {e}")

    # 14. Conversation 领域
    try:
        from app.neuro_bus.domains.conversation_domain_handlers import (
            register_conversation_domain_handlers,
        )

        register_conversation_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Conversation 领域处理器注册完成")
    except ImportError:
        logger.info("[NeuroDomainRegistration] Conversation 领域处理器不存在，跳过")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Conversation 领域注册失败: {e}")

    logger.info("[NeuroDomainRegistration] 所有领域处理器注册完成")


async def register_all_domains_complete(bus: NeuroBus | None = None) -> None:
    """
    注册 NeuroDomain 类 + 全部 handler 模块（兼容旧入口）。
    """
    if bus is None:
        bus = get_neuro_bus()

    logger.info("[NeuroDomainRegistration] 开始注册所有 12 个领域处理器（含 NeuroDomain）")
    try:
        from app.neuro_bus.register_all_neuro_domains import register_all_neuro_domains

        register_all_neuro_domains()
        logger.info("[NeuroDomainRegistration] 基础领域处理器注册完成")
    except Exception as e:
        logger.warning(f"[NeuroDomainRegistration] 基础领域注册部分失败: {e}")

    await register_domain_handlers_only(bus)


def init_neuro_bus_complete() -> NeuroBus:
    """
    初始化 NeuroBus 并注册所有领域处理器（含 handler 模块）。
    无运行中事件循环时使用 ``asyncio.run``；已在循环内时调度 ``register_neuro_runtime`` 任务。
    """
    from app.neuro_bus.register_runtime import register_neuro_runtime

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(register_neuro_runtime())
    else:
        asyncio.create_task(register_neuro_runtime())
    return get_neuro_bus()


# 快捷函数
register_all = register_all_domains_complete
init_bus = init_neuro_bus_complete


if __name__ == "__main__":
    # 测试注册
    logging.basicConfig(level=logging.INFO)

    print("[TEST] 测试注册所有领域处理器（完整版）")
    bus = init_neuro_bus_complete()
    print(f"[TEST] NeuroBus 状态: running={bus._running}")
    print("[TEST] 注册完成")
