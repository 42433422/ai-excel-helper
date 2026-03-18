#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查app_api.py的语法错误
"""

import ast

try:
    with open('app_api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 尝试解析代码
    ast.parse(content)
    print("✅ 语法正确，没有缩进错误")
except IndentationError as e:
    print(f"❌ 缩进错误: {e}")
    print(f"   行号: {e.lineno}")
    print(f"   偏移量: {e.offset}")
    # 显示错误行附近的代码
    lines = content.split('\n')
    start_line = max(0, e.lineno - 3)
    end_line = min(len(lines), e.lineno + 2)
    print("\n错误位置附近的代码:")
    for i in range(start_line, end_line):
        line_num = i + 1
        marker = " -> " if line_num == e.lineno else "    "
        print(f"{marker}{line_num:4d}: {lines[i]}")
except SyntaxError as e:
    print(f"❌ 语法错误: {e}")
    print(f"   行号: {e.lineno}")
    print(f"   偏移量: {e.offset}")
    # 显示错误行附近的代码
    lines = content.split('\n')
    start_line = max(0, e.lineno - 3)
    end_line = min(len(lines), e.lineno + 2)
    print("\n错误位置附近的代码:")
    for i in range(start_line, end_line):
        line_num = i + 1
        marker = " -> " if line_num == e.lineno else "    "
        print(f"{marker}{line_num:4d}: {lines[i]}")
except Exception as e:
    print(f"❌ 其他错误: {e}")
