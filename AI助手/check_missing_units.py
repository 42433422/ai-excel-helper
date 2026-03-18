#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Excel文件中哪些单位缺失，并恢复它们的产品
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "templates\\新建 XLSX 工作表 (2).xlsx"

def check_missing_units():
    """检查Excel中缺失的购买单位"""
    try:
        # 读取Excel数据
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        
        # 获取Excel中的所有购买单位
        excel_units = set(df['购买单位'].dropna().unique())
        
        # 我们期望的购买单位（24个）
        expected_units = {
            '蕊芯家私', '蕊芯家私1', '陈鑫强',  # 原有单位
            '金汉武', '金汉武（宾驰）', '半岛风情', '国邦:钟志勇',
            '侯雪梅', '金汉武鼎丰：国邦', '金汉武三江源', '名品（晶美鑫）',
            '澜宇', '七彩乐园', '温总', '杰妮熊', '小火洋', '鑫顺',
            '奔奔熊鞋柜', '博旺家私', '宜榢', '迎扬电视墙',
            '中江博郡家私', '志泓家私', '宗南家私'
        }
        
        # 找出缺失的单位
        missing_units = expected_units - excel_units
        
        logger.info(f"Excel中的单位 ({len(excel_units)} 个):")
        for unit in sorted(excel_units):
            logger.info(f"  - {unit}")
        
        logger.info(f"\n缺失的单位 ({len(missing_units)} 个):")
        for unit in sorted(missing_units):
            logger.info(f"  - {unit}")
        
        # 检查额外的单位（Excel中有但不在期望列表中的）
        extra_units = excel_units - expected_units
        logger.info(f"\n额外的单位 ({len(extra_units)} 个):")
        for unit in sorted(extra_units):
            logger.info(f"  - {unit}")
        
        return missing_units, extra_units
        
    except Exception as e:
        logger.error(f"检查缺失单位失败: {e}")
        return set(), set()

def main():
    """主函数"""
    print("=== 检查Excel文件中缺失的购买单位 ===")
    missing_units, extra_units = check_missing_units()
    print(f"\n结果:")
    print(f"  - Excel文件中有 {len(extra_units) + len(missing_units)} 个单位")
    print(f"  - 缺失 {len(missing_units)} 个单位的原始数据")

if __name__ == "__main__":
    main()
