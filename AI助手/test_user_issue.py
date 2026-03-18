#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用户报告的产品匹配问题
输入: 七彩乐园P白底漆10桶，规格25.0
"""

import logging
from shipment_parser import ShipmentParser
from ai_augmented_parser import AIAugmentedShipmentParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_user_issue():
    """测试用户报告的问题"""
    test_input = "七彩乐园P白底漆10桶，规格25.0"
    
    logger.info(f"测试输入: {test_input}")
    
    # 测试传统解析器
    logger.info("=== 测试传统解析器 ===")
    parser = ShipmentParser()
    result = parser.parse(test_input)
    
    logger.info(f"购买单位: {result.purchase_unit}")
    logger.info(f"产品数量: {len(result.products)}")
    for i, product in enumerate(result.products):
        logger.info(f"产品{i+1}: {product['name']} - {product['quantity_tins']}桶, {product['quantity_kg']}kg, 规格{product['tin_spec']}kg/桶, 单价{product['unit_price']}")
    logger.info(f"有效: {result.is_valid()}")
    
    # 测试AI增强解析器
    logger.info("\n=== 测试AI增强解析器 ===")
    ai_parser = AIAugmentedShipmentParser()
    ai_result = ai_parser.parse(test_input)
    
    logger.info(f"购买单位: {ai_result.purchase_unit}")
    logger.info(f"产品数量: {len(ai_result.products)}")
    for i, product in enumerate(ai_result.products):
        logger.info(f"产品{i+1}: {product['name']} - {product['quantity_tins']}桶, {product['quantity_kg']}kg, 规格{product['tin_spec']}kg/桶, 单价{product['unit_price']}")
    logger.info(f"有效: {ai_result.is_valid()}")
    
    # 测试语音优化功能
    logger.info("\n=== 测试语音优化功能 ===")
    optimized_text = ai_parser.optimize_voice_recognition(test_input)
    logger.info(f"优化后的文本: {optimized_text}")
    
    # 测试优化后的解析
    logger.info("\n=== 测试优化后的解析 ===")
    optimized_result = ai_parser.parse(optimized_text)
    
    logger.info(f"购买单位: {optimized_result.purchase_unit}")
    logger.info(f"产品数量: {len(optimized_result.products)}")
    for i, product in enumerate(optimized_result.products):
        logger.info(f"产品{i+1}: {product['name']} - {product['quantity_tins']}桶, {product['quantity_kg']}kg, 规格{product['tin_spec']}kg/桶, 单价{product['unit_price']}")
    logger.info(f"有效: {optimized_result.is_valid()}")

if __name__ == "__main__":
    test_user_issue()
