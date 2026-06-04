#!/usr/bin/env python3
"""
注册所有 Neuro 领域事件处理器 V2

扩展 register_all_neuro_domains，添加 Product 和 Shipment 领域。
"""

import logging
import asyncio
from typing import Optional

from app.neuro_bus.bus import get_neuro_bus, NeuroBus

logger = logging.getLogger(__name__)


async def register_all_neuro_domains_v2(bus: Optional[NeuroBus] = None) -> None:
    """
    注册所有领域事件处理器（增强版）

    包含以下领域：
    1. 基础领域（原有）: intent, order, inventory, customer, ai_service, wechat, print, ocr, payment, safety
    2. 新增领域: product, shipment
    """
    if bus is None:
        bus = get_neuro_bus()

    logger.info("[NeuroDomainRegistration] 开始注册所有领域处理器 V2")

    # 1. 先注册原有领域处理器
    try:
        from app.neuro_bus.register_all_neuro_domains import register_all_neuro_domains

        register_all_neuro_domains()
        logger.info("[NeuroDomainRegistration] 原有领域处理器注册完成")
    except Exception as e:
        logger.warning(f"[NeuroDomainRegistration] 原有领域注册失败或部分失败: {e}")

    # 2. 注册 Product 领域处理器
    try:
        from app.neuro_bus.domains.product_domain_handlers import register_product_domain_handlers

        register_product_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Product 领域处理器注册完成")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Product 领域注册失败: {e}")

    # 3. 注册 Shipment 领域处理器
    try:
        from app.neuro_bus.domains.shipment_domain_handlers import register_shipment_domain_handlers

        register_shipment_domain_handlers(bus)
        logger.info("[NeuroDomainRegistration] Shipment 领域处理器注册完成")
    except Exception as e:
        logger.error(f"[NeuroDomainRegistration] Shipment 领域注册失败: {e}")

    logger.info("[NeuroDomainRegistration] 所有领域处理器注册完成 V2")


def init_neuro_bus_with_all_domains() -> NeuroBus:
    """
    初始化 NeuroBus 并注册所有领域处理器

    Returns:
        初始化完成的 NeuroBus 实例
    """
    bus = get_neuro_bus()

    # 异步注册
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环已在运行，创建任务
            asyncio.create_task(register_all_neuro_domains_v2(bus))
        else:
            # 否则直接运行
            loop.run_until_complete(register_all_neuro_domains_v2(bus))
    except RuntimeError:
        # 没有事件循环，创建新的
        asyncio.run(register_all_neuro_domains_v2(bus))

    return bus


# 向后兼容的别名
register_all_neuro_domains_enhanced = register_all_neuro_domains_v2


if __name__ == "__main__":
    # 测试注册
    logging.basicConfig(level=logging.INFO)

    print("[TEST] 测试注册所有领域处理器")
    bus = init_neuro_bus_with_all_domains()
    print(f"[TEST] NeuroBus 状态: running={bus._running}")
    print("[TEST] 注册完成")
