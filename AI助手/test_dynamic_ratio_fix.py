#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的标签生成器 - 动态配比显示
"""

import os
import sys

# 添加当前目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from label_generator import ProductLabelGenerator
from ratio_rules_manager_fixed import RatioRulesManager
from PIL import Image, ImageDraw

def test_dynamic_ratio_labels():
    """测试动态配比标签生成"""
    print("🧪 测试修复后的动态配比标签生成")
    print("=" * 60)
    
    # 创建商标导出目录
    LABELS_EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '商标导出')
    os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)
    
    # 创建参考配比规则管理器
    ratio_manager = RatioRulesManager()
    generator = ProductLabelGenerator()
    
    # 测试数据 - 不同类型的漆应该显示不同的配比
    test_data_list = [
        {
            'name': 'PU底漆（4列配比）',
            'data': {
                'product_number': 'TEST-001',
                'product_name': 'PU底漆',  # 不包含"剂"，应该显示参考配比
                'ratio': '主剂：固化剂：稀释剂：催化剂，1：0.6-0.7：0.4-0.6：0.1-0.2',
                'production_date': '2026.02.01',
                'shelf_life': '6个月',
                'specification': '15±0.1KG',
                'inspector': '合格'
            }
        },
        {
            'name': 'PE底漆（4列配比）',
            'data': {
                'product_number': 'TEST-002',
                'product_name': 'PE底漆',  # 不包含"剂"，应该显示参考配比
                'ratio': '主剂：兰水：稀释剂：白水，100 : 1.2-1.5 : 50-70 : 1.5-1.8',
                'production_date': '2026.02.01',
                'shelf_life': '6个月',
                'specification': '20±0.1KG',
                'inspector': '合格'
            }
        },
        {
            'name': 'PU亮光漆（3列配比）',
            'data': {
                'product_number': 'TEST-003',
                'product_name': 'PU亮光漆',  # 不包含"剂"，应该显示参考配比
                'ratio': '主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7',
                'production_date': '2026.02.01',
                'shelf_life': '6个月',
                'specification': '25±0.1KG',
                'inspector': '合格'
            }
        },
        {
            'name': 'PU哑光漆（3列配比）',
            'data': {
                'product_number': 'TEST-004',
                'product_name': 'PU哑光漆',  # 不包含"剂"，应该显示参考配比
                'ratio': '主剂：固化剂：稀释剂，1：0.5-0.6：0.4-0.8',
                'production_date': '2026.02.01',
                'shelf_life': '6个月',
                'specification': '30±0.1KG',
                'inspector': '合格'
            }
        },
        {
            'name': '硝基漆（2列配比）',
            'data': {
                'product_number': 'TEST-005',
                'product_name': '硝基漆',  # 不包含"剂"，应该显示参考配比
                'ratio': '主剂：稀释剂，1：0.8-1',
                'production_date': '2026.02.01',
                'shelf_life': '6个月',
                'specification': '35±0.1KG',
                'inspector': '合格'
            }
        },
        {
            'name': 'PU固化剂（不显示配比）',
            'data': {
                'product_number': 'TEST-006',
                'product_name': 'PU固化剂',  # 包含"剂"，应该不显示参考配比
                'ratio': '主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7',
                'production_date': '2026.02.01',
                'shelf_life': '6个月',
                'specification': '40±0.1KG',
                'inspector': '合格'
            }
        }
    ]
    
    for i, test_item in enumerate(test_data_list, 1):
        test_data = test_item['data'].copy()
        product_name = test_data['product_name']
        
        print(f"\n🏷️ 测试 {i}: {test_item['name']}")
        print(f"   产品名称: {product_name}")
        
        # 检查是否包含"剂"或"料"
        contains_ji_or_liao = any(keyword in product_name for keyword in ['剂', '料'])
        
        if contains_ji_or_liao:
            print(f"   包含'剂'或'料': 是")
            print(f"   显示参考配比: 否")
            print(f"   配比数据: {test_data['ratio']} (但不会显示)")
        else:
            print(f"   包含'剂'或'料': 否")
            print(f"   显示参考配比: 是")
            print(f"   配比数据: {test_data['ratio']}")
            
            # 尝试匹配参考配比
            matched_ratio = ratio_manager.match_ratio_by_product_name(product_name)
            if matched_ratio:
                test_data['ratio'] = matched_ratio
                print(f"   自动匹配配比: {matched_ratio}")
        
        # 生成标签
        filename = f"dynamic_ratio_test_{i}_{test_item['name'].replace('（', '_').replace('）', '').replace(' ', '_')}.png"
        output_path = os.path.join(LABELS_EXPORT_DIR, filename)
        
        try:
            generator.generate_label(test_data, output_path)
            print(f"   标签文件: {filename} ✅")
        except Exception as e:
            print(f"   标签生成失败: {e} ❌")
    
    print(f"\n✅ 动态配比标签测试完成！")

def test_ratio_parsing():
    """测试配比数据解析"""
    print("\n🧪 测试配比数据解析")
    print("=" * 60)
    
    # 测试不同格式的配比数据
    test_ratios = [
        '主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7',  # 3列
        '主剂：兰水：稀释剂：白水，100 : 1.2-1.5 : 50-70 : 1.5-1.8',  # 4列
        '主剂：稀释剂，1：0.8-1',  # 2列
        '主剂：催化剂：稀释剂：流平剂，1：0.1-0.2：0.4-0.6：0.05-0.1',  # 4列
    ]
    
    for i, ratio_text in enumerate(test_ratios, 1):
        print(f"\n📊 测试 {i}: {ratio_text}")
        
        # 模拟解析逻辑 - 与标签生成器保持一致
        try:
            if '，' in ratio_text:
                # 格式：表头，数值
                parts = ratio_text.split('，', 1)
                headers_text = parts[0].strip()
                values_text = parts[1].strip()
                
                # 解析表头 - 使用中文分号
                headers = [h.strip() for h in headers_text.split('：')]
                
                # 解析数值 - 处理中文和英文冒号的混合
                # 先替换中文冒号为英文冒号，然后分割
                values_text_normalized = values_text.replace('：', ':').replace(' ', '')
                values = [v.strip() for v in values_text_normalized.split(':')]
            else:
                # 格式：主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7
                # 默认表头
                headers = ["主剂", "固化剂", "稀释剂"]
                values = ["1", "0.7-0.8", "0.5-0.7"]
            
            # 动态计算列数
            num_columns = len(headers)
            if len(values) != num_columns:
                values = values[:num_columns] + ['0'] * (num_columns - len(values))
            
            print(f"   解析结果:")
            print(f"   列数: {num_columns}")
            print(f"   表头: {headers}")
            print(f"   数值: {values}")
            print(f"   解析状态: 成功 ✅")
            
        except Exception as e:
            print(f"   解析失败: {e} ❌")

if __name__ == '__main__':
    # 测试配比解析
    test_ratio_parsing()
    
    # 测试动态配比标签
    test_dynamic_ratio_labels()
    
    print("\n🎉 修复验证完成！")
