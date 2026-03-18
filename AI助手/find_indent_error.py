#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定位app_api.py中的缩进错误
"""

import re

try:
    with open('app_api.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"正在检查 {len(lines)} 行代码...")
    
    # 检查每一行的缩进
    for i, line in enumerate(lines, 1):
        # 跳过空行
        stripped = line.strip()
        if not stripped:
            continue
        
        # 计算缩进
        indent = len(line) - len(line.lstrip())
        
        # 检查缩进是否为4的倍数
        if indent % 4 != 0:
            print(f"⚠️  行 {i}: 缩进不是4的倍数 ({indent} 空格)")
            print(f"   代码: {stripped}")
        
        # 检查是否有混合缩进（制表符和空格）
        if '\t' in line[:indent]:
            print(f"⚠️  行 {i}: 混合使用了制表符和空格")
            print(f"   代码: {stripped}")
    
    print("\n✅ 缩进检查完成")
    
    # 尝试运行Python的py_compile模块
    print("\n尝试使用py_compile检查...")
    import py_compile
    py_compile.compile('app_api.py')
    print("✅ py_compile检查通过")
    
except Exception as e:
    print(f"❌ 检查时出错: {e}")
