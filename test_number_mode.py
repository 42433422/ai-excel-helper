#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试编号模式功能
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_number_mode():
    """测试编号模式功能"""
    logger.info("开始测试编号模式功能")
    
    # 导入模块
    from shipment_parser import ShipmentParser
    
    # 初始化解析器
    parser = ShipmentParser()
    
    # 测试用例
    test_cases = [
        {
            "name": "七彩乐园一桶9803规格28",
            "expected_model": "9803",
            "description": "测试编号模式识别"
        },
        {
            "name": "蕊芯10桶9806规格28",
            "expected_model": "9806",
            "description": "测试数字模式识别"
        },
        {
            "name": "1桶9806a规格280",
            "expected_model": "9806a",
            "description": "测试字母数字混合模式"
        }
    ]
    
    for test_case in test_cases:
        logger.info(f"测试: {test_case['description']}")
        logger.info(f"输入: {test_case['name']}")
        
        # 测试编号模式
        result = parser._match_product_from_db(test_case['name'], number_mode=True)
        if result:
            logger.info(f"✓ 匹配成功: {result['name']}, 型号: {result['model_number']}")
        else:
            logger.warning(f"✗ 未匹配到产品")
        
        # 测试普通模式
        result_normal = parser._match_product_from_db(test_case['name'], number_mode=False)
        if result_normal:
            logger.info(f"  普通模式匹配: {result_normal['name']}, 型号: {result_normal['model_number']}")
        else:
            logger.warning(f"  普通模式未匹配到产品")
        
        logger.info("-" * 50)

def test_purchase_unit_contact():
    """测试购买单位联系人信息获取"""
    logger.info("测试购买单位联系人信息获取")
    
    # 导入模块
    from shipment_parser import ShipmentParser
    
    parser = ShipmentParser()
    
    # 测试获取购买单位信息
    units = parser._load_purchase_units_from_db()
    logger.info(f"成功加载 {len(units)} 个购买单位")
    
    # 显示前5个购买单位信息
    for i, (unit_name, unit_info) in enumerate(list(units.items())[:5]):
        logger.info(f"{unit_name}: 联系人={unit_info['contact_person']}, 电话={unit_info['contact_phone']}")

if __name__ == "__main__":
    # 切换到AI助手目录
    os.chdir('AI助手')
    
    logger.info("=== 编号模式功能测试 ===")
    test_number_mode()
    
    logger.info("\n=== 购买单位联系人测试 ===")
    test_purchase_unit_contact()
    
    logger.info("测试完成")
