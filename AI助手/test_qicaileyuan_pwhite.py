#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试七彩乐园P白底产品识别
"""

import logging
from ai_augmented_parser import AIAugmentedShipmentParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qicaileyuan_pwhite():
    """测试七彩乐园P白底产品识别"""
    test_cases = [
        "七彩乐园P白底10桶，规格25",
        "七彩乐园P白底漆10桶，规格25",
        "七彩乐园PE白底10桶，规格25",
        "七彩乐园PE白底漆10桶，规格25"
    ]
    
    ai_parser = AIAugmentedShipmentParser()
    
    for i, test_input in enumerate(test_cases):
        logger.info(f"\n=== 测试用例 {i+1}: {test_input} ===")
        
        # 语音优化
        optimized_text = ai_parser.optimize_voice_recognition(test_input)
        logger.info(f"优化后的文本: {optimized_text}")
        
        # AI解析
        result = ai_parser.parse(optimized_text)
        
        logger.info(f"购买单位: {result.purchase_unit}")
        logger.info(f"产品数量: {len(result.products)}")
        for j, product in enumerate(result.products):
            logger.info(f"产品{j+1}: {product['name']} - {product['model_number']}, {product['quantity_tins']}桶, {product['quantity_kg']}kg, 规格{product['tin_spec']}kg/桶, 单价{product['unit_price']}, 金额{product['amount']}")
        logger.info(f"总金额: {result.amount}")
        logger.info(f"解析有效: {result.is_valid()}")
        
        # 验证关键信息
        if result.purchase_unit == "七彩乐园":
            logger.info("✓ 购买单位识别成功: 七彩乐园")
        else:
            logger.warning("✗ 购买单位识别失败")
        
        if result.products:
            product = result.products[0]
            if "白底漆" in product['name'] or "白底" in product['name']:
                logger.info(f"✓ 产品识别成功: {product['name']}")
            else:
                logger.warning(f"✗ 产品识别可能不准确: {product['name']}")
            
            if product['model_number'] == "9803A":
                logger.info("✓ 产品型号匹配成功: 9803A")
            else:
                logger.info(f"产品型号: {product['model_number']}")
        else:
            logger.warning("✗ 产品识别失败")

if __name__ == "__main__":
    test_qicaileyuan_pwhite()
