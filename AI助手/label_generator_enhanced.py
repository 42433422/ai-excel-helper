#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版标签生成器 - 集成参考配比规则
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from label_generator import ProductLabelGenerator
from ratio_rules_manager_fixed import RatioRulesManager
from PIL import Image, ImageDraw

class EnhancedProductLabelGenerator(ProductLabelGenerator):
    def __init__(self):
        super().__init__()
        self.ratio_manager = RatioRulesManager()
    
    def generate_label(self, product_data, output_path):
        image = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(image)
        
        draw.rectangle([0, 0, self.width-1, self.height-1], outline=self.border_color, width=3)
        
        # 判断产品名称是否包含"剂"或"料"，决定是否显示参考配比
        product_name = product_data.get('product_name', '')
        contains_ji_or_liao = any(keyword in product_name for keyword in ['剂', '料'])
        
        # 如果不包含"剂"或"料"，则显示参考配比，并且根据关键词匹配
        has_ratio = not contains_ji_or_liao
        
        # 如果要显示参考配比，则从数据库中匹配对应的配比
        if has_ratio:
            matched_ratio = self.ratio_manager.match_ratio_by_product_name(product_name)
            if matched_ratio:
                product_data['ratio'] = matched_ratio  # 更新配比数据
        
        # 继续原有的标签生成逻辑
        return super().generate_label(product_data, output_path)

# 测试代码
if __name__ == '__main__':
    from datetime import datetime
    import uuid
    
    # 商标导出目录
    LABELS_EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '商标导出')
    os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)
    
    # 测试数据
    test_data_list = [
        {
            'product_number': 'TEST-001',
            'product_name': 'PU底漆固化剂',  # 包含"剂"，应该不显示参考配比
            'ratio': '1:0.5-0.6:0.5-0.8',
            'production_date': '2026.02.01',
            'shelf_life': '6个月',
            'specification': '15±0.1KG',
            'inspector': '合格'
        },
        {
            'product_number': 'TEST-002',
            'product_name': 'PU底漆',  # 不包含"剂"，应该显示参考配比
            'ratio': '1:0.5-0.6:0.5-0.8',
            'production_date': '2026.02.01',
            'shelf_life': '6个月',
            'specification': '20±0.1KG',
            'inspector': '合格'
        },
        {
            'product_number': 'TEST-003',
            'product_name': 'PU亮光漆',  # 不包含"剂"，应该显示参考配比
            'ratio': '1:0.5-0.6:0.5-0.8',
            'production_date': '2026.02.01',
            'shelf_life': '6个月',
            'specification': '25±0.1KG',
            'inspector': '合格'
        }
    ]
    
    print("🧪 测试增强版标签生成器")
    print("=" * 50)
    
    generator = EnhancedProductLabelGenerator()
    
    for i, test_data in enumerate(test_data_list, 1):
        filename = f"enhanced_test_{i}_{uuid.uuid4().hex[:8]}.png"
        output_path = os.path.join(LABELS_EXPORT_DIR, filename)
        
        print(f"\n📦 测试 {i}: {test_data['product_name']}")
        print(f"   包含'剂'或'料': {'是' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '否'}")
        print(f"   是否显示参考配比: {'否' if any(kw in test_data['product_name'] for kw in ['剂', '料']) else '是'}")
        
        # 检查匹配结果
        if not any(kw in test_data['product_name'] for kw in ['剂', '料']):
            matched_ratio = generator.ratio_manager.match_ratio_by_product_name(test_data['product_name'])
            print(f"   匹配到的配比: {matched_ratio if matched_ratio else '无匹配'}")
        
        generator.generate_label(test_data, output_path)
        print(f"   标签文件: {filename}")
    
    print(f"\n✅ 增强版标签生成完成！")
