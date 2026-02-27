#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查打印机状态和配置
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from print_utils import get_printers

def check_printers():
    """检查打印机状态"""
    print("检查打印机配置...")
    
    try:
        printers = get_printers()
        print(f"找到 {len(printers)} 个打印机:")
        
        for i, printer in enumerate(printers):
            name = printer.get('name', 'Unknown')
            printer_type = printer.get('type', '未分类')
            status = printer.get('status', '未知')
            is_default = printer.get('is_default', False)
            
            print(f"  {i+1}. {name}")
            print(f"     类型: {printer_type}")
            print(f"     状态: {status}")
            print(f"     默认: {'是' if is_default else '否'}")
            print()
        
        # 检查打印机识别逻辑
        print("=== 打印机识别分析 ===")
        for i, printer in enumerate(printers):
            name = printer.get('name', '').lower()
            print(f"打印机 {i+1}: {printer.get('name', '')}")
            
            # 发货单打印机识别
            if any(keyword in name for keyword in ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式']):
                print(f"  -> 识别为发货单打印机 (Jolimark关键词)")
            # 标签打印机识别
            elif any(keyword in name for keyword in ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode']):
                print(f"  -> 识别为标签打印机 (TSC关键词)")
            else:
                print(f"  -> 未识别为专用打印机")
            print()
                
    except Exception as e:
        print(f"检查打印机失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_printers()
