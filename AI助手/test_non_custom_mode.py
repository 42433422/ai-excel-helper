#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试非自定义模式下的产品匹配逻辑
确保系统只匹配产品库里已有的产品
"""

import logging
from shipment_parser import ShipmentParser
from ai_augmented_parser import AIAugmentedShipmentParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_non_custom_mode():
    """测试非自定义模式"""
    test_cases = [
        # 应该匹配到的产品（产品库里有）
        "七彩乐园PE白底漆10桶，规格25",
        "蕊芯PE白底漆5桶，规格28",
        
        # 不应该匹配到的产品（产品库里没有）
        "七彩乐园不存在的产品10桶，规格25",
        "蕊芯测试产品5桶，规格20"
    ]
    
    parser = ShipmentParser()
    ai_parser = AIAugmentedShipmentParser()
    
    for i, test_input in enumerate(test_cases):
        logger.info(f"\n=== 测试用例 {i+1}: {test_input} ===")
        
        # 测试传统解析器（非自定义模式）
        logger.info("1. 传统解析器（非自定义模式）")
        result = parser.parse(test_input, custom_mode=False)
        
        logger.info(f"购买单位: {result.purchase_unit}")
        logger.info(f"产品数量: {len(result.products)}")
        for j, product in enumerate(result.products):
            logger.info(f"产品{j+1}: {product['name']} - {product['model_number']}, {product['quantity_tins']}桶, {product['quantity_kg']}kg, 单价{product['unit_price']}")
        logger.info(f"解析有效: {result.is_valid()}")
        
        # 测试AI增强解析器（非自定义模式）
        logger.info("2. AI增强解析器（非自定义模式）")
        ai_result = ai_parser.parse(test_input, custom_mode=False)
        
        logger.info(f"购买单位: {ai_result.purchase_unit}")
        logger.info(f"产品数量: {len(ai_result.products)}")
        for j, product in enumerate(ai_result.products):
            logger.info(f"产品{j+1}: {product['name']} - {product['model_number']}, {product['quantity_tins']}桶, {product['quantity_kg']}kg, 单价{product['unit_price']}")
        logger.info(f"解析有效: {ai_result.is_valid()}")
        
        # 验证结果
        logger.info("3. 验证结果")
        if "不存在" in test_input or "测试产品" in test_input:
            # 这些产品应该匹配失败
            if not result.is_valid() or not result.products:
                logger.info("✓ 正确：非自定义模式下，未匹配到不存在的产品")
            else:
                logger.warning("✗ 错误：非自定义模式下，匹配到了不存在的产品")
        else:
            # 这些产品应该匹配成功
            if result.is_valid() and result.products:
                logger.info("✓ 正确：非自定义模式下，成功匹配到产品库里的产品")
            else:
                logger.warning("✗ 错误：非自定义模式下，未匹配到产品库里的产品")

if __name__ == "__main__":
    test_non_custom_mode()
