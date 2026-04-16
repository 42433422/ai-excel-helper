"""简单测试产品解析"""

import re

def test_patterns():
    user_message = "打印一下深圳市百木鼎家具有限公司的销售合同需要两桶 3721 和一桶 308"
    
    patterns = [
        # 原有模式：编号 3721 要三桶
        r'编号\s*(\w+)\s*[要 x×]\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
        # 新增模式：需要两桶 3721 (数量在前)
        r'(?:需要 | 要)\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\w+)',
        # 新增模式：两桶 3721 (简单模式，产品型号为数字)
        r'(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\d{3,4})',
        # 新增模式：3721 两桶 (产品在前，产品型号为数字)
        r'(\d{3,4})\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
    ]
    
    print(f"用户输入：{user_message}\n")
    
    for i, pattern in enumerate(patterns, 1):
        print(f"模式{i}: {pattern}")
        matches = list(re.finditer(pattern, user_message))
        if matches:
            print(f"  ✅ 匹配到 {len(matches)} 个结果:")
            for match in matches:
                print(f"    分组：{match.groups()}")
        else:
            print(f"  ❌ 无匹配")
        print()

if __name__ == "__main__":
    test_patterns()
