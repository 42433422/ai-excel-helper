#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整的语音输入到产品匹配工作流程
"""

import logging
from ai_augmented_parser import AIAugmentedShipmentParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_complete_workflow():
    """测试完整的工作流程"""
    test_cases = [
        "七彩乐园P白底漆10桶，规格25.0",
        "蕊芯PE白底漆5桶，规格28",
        "金汉武哑光银珠漆2桶，规格20",
        "七彩乐园PE稀释剂1桶，规格180"
    ]
    
    ai_parser = AIAugmentedShipmentParser()
    
    for i, test_input in enumerate(test_cases):
        logger.info(f"\n=== 测试用例 {i+1}: {test_input} ===")
        
        # 1. 语音优化
        logger.info("1. 语音优化")
        optimized_text = ai_parser.optimize_voice_recognition(test_input)
        logger.info(f"优化后的文本: {optimized_text}")
        
        # 2. AI解析
        logger.info("2. AI解析")
        result = ai_parser.parse(optimized_text)
        
        logger.info(f"购买单位: {result.purchase_unit}")
        logger.info(f"产品数量: {len(result.products)}")
        for j, product in enumerate(result.products):
            logger.info(f"产品{j+1}: {product['name']} - {product['quantity_tins']}桶, {product['quantity_kg']}kg, 规格{product['tin_spec']}kg/桶, 单价{product['unit_price']}, 金额{product['amount']}")
        logger.info(f"总金额: {result.amount}")
        logger.info(f"解析有效: {result.is_valid()}")
        
        # 3. 验证关键信息
        logger.info("3. 验证关键信息")
        if result.purchase_unit:
            logger.info(f"✓ 购买单位识别成功: {result.purchase_unit}")
        else:
            logger.warning("✗ 购买单位识别失败")
        
        if result.products:
            logger.info(f"✓ 产品识别成功: {len(result.products)}个产品")
        else:
            logger.warning("✗ 产品识别失败")

if __name__ == "__main__":
    test_complete_workflow()
