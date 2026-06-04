"""
调试产品提取
"""

import re

test_input = "需要两桶 3721 和一桶 308"

# 测试正则
pattern = r"(?:需要 | 要)?(\d+|[零一二两三四五六七八九十百千]+)\s*桶\s*(?:编号)?(\d{3,4}[A-Za-z]*)"
print(f"测试正则：{pattern}")
print(f"输入：{test_input}")
print("\n匹配结果:")
for match in re.finditer(pattern, test_input):
    print(f"  全匹配：{match.group(0)}")
    print(f"  数量：'{match.group(1)}'")
    print(f"  型号：{match.group(2)}")
    qty_check = re.match(r"^(\d+|[零一二两三四五六七八九十百千]+)$", match.group(1))
    print(f"  数量验证：{qty_check}")
