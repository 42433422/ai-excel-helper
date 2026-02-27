#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试语音识别优化功能
"""

import logging
import json
from ai_augmented_parser import AIAugmentedShipmentParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_voice_optimization():
    """测试语音识别优化功能"""
    print("=== 测试语音识别优化功能 ===")
    
    # 创建AI解析器实例
    ai_parser = AIAugmentedShipmentParser()
    
    # 测试用例
    test_cases = [
        "七彩乐园P白底漆10桶，规格25.0",
        "七彩乐园PE白底漆10桶，规格25",
        "彩乐园P，百里奚石头。规格，25",
        "七彩乐园PE白底10桶，PE稀释剂180kg1桶",
        "蕊芯家私:Pe白底漆10桶，规格28KG"
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_text}")
        
        try:
            # 测试AI产品提取
            ai_result = ai_parser._call_deepseek_for_product_extraction(test_text, False)
            print(f"AI提取结果: {json.dumps(ai_result, ensure_ascii=False, indent=2)}")
            
            # 测试语音识别优化
            optimized_text = ai_parser.optimize_voice_recognition(test_text)
            print(f"优化后文本: {optimized_text}")
            
            # 测试完整解析
            parsed_result = ai_parser.parse(test_text)
            print(f"解析结果 - 购买单位: {parsed_result.purchase_unit}")
            print(f"解析结果 - 产品数量: {len(parsed_result.products)}")
            for j, product in enumerate(parsed_result.products, 1):
                print(f"产品 {j}: {product['name']} - {product['quantity_tins']}桶, 规格{product['tin_spec']}")
            
        except Exception as e:
            logger.error(f"测试失败: {e}")
            print(f"测试失败: {e}")
        
        print("-" * 80)

if __name__ == "__main__":
    test_voice_optimization()
