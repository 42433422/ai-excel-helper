"""调试正则表达式"""

import re

text = "帮我打印销售合同客户名称是深圳市百木鼎家具有限公司，编号 3721 要三桶"

patterns = [
    r'编号\s*(\d{3,4})\s*[要 x×]\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
    r'(?:需要 | 要)\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\d{3,4})',
    r'(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\d{3,4})',
    r'(\d{3,4})\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
]

for i, pattern in enumerate(patterns, 1):
    print(f"模式{i}: {pattern}")
    matches = list(re.finditer(pattern, text))
    if matches:
        print(f"  ✅ 匹配到：{[(m.groups(), m.group()) for m in matches]}")
    else:
        print(f"  ❌ 无匹配")
    print()
