"""
销售合同意图识别和槽位提取测试（简化版 - 不依赖数据库）

测试多种用户表达方式的意图识别和槽位提取能力
"""

import re


def test_pattern_matching():
    """测试正则表达式模式匹配"""
    
    print("=" * 80)
    print("销售合同意图识别和槽位提取测试（简化版）")
    print("=" * 80)
    print()
    
    # 测试用例
    test_cases = [
        # (用户输入，期望识别的产品和数量)
        ("帮我打印销售合同客户名称是深圳市百木鼎家具有限公司，编号 3721 要三桶", 
         [("3721", 3)]),
        
        ("打印一下深圳市百木鼎家具有限公司的销售合同需要两桶 3721 和一桶 308",
         [("3721", 2), ("308", 1)]),
        
        ("销售合同 两桶 3721 一桶 308",
         [("3721", 2), ("308", 1)]),
        
        ("3721 两桶，308 一桶",
         [("3721", 2), ("308", 1)]),
        
        ("深圳市百木鼎家具有限公司 编号 3721 要三桶，还需要两桶 308",
         [("3721", 3), ("308", 2)]),
        
        ("广东华天家具有限公司要 5 桶 9803，3 桶 779，还有 2 桶 3721",
         [("9803", 5), ("779", 3), ("3721", 2)]),
        
        ("七彩乐园那个单，9803 来 10 桶，308 来 5 桶",
         [("9803", 10), ("308", 5)]),
        
        ("需要三十二桶 3721 和十五桶 308",
         [("3721", 32), ("308", 15)]),
        
        ("3721 五桶",
         [("3721", 5)]),
    ]
    
    # 多模式正则表达式
    patterns = [
        # 原有模式：编号 3721 要三桶
        r'编号\s*(\w+)\s*[要 x×]\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
        # 新增模式：需要两桶 3721 (数量在前)
        r'(?:需要 | 要)\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\w+)',
        # 新增模式：两桶 3721 (简单模式，产品型号为数字)
        r'(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\d{3,4})',
        # 新增模式：3721 两桶 (产品在前，产品型号为数字)
        r'(\d{3,4})\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
        # 通用模式：产品型号 + 数量
        r'(\w+)\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
    ]
    
    # 中文字符数字映射
    chinese_num = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, 
                   "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100}
    
    def parse_qty(s: str) -> int:
        """解析数量"""
        s = s.strip()
        try:
            return int(s)
        except ValueError:
            return chinese_num.get(s, 1)
    
    # 运行测试
    for i, (user_input, expected) in enumerate(test_cases, 1):
        print(f"测试 {i}: {user_input}")
        print(f"  期望结果：{expected}")
        
        # 尝试所有模式
        extracted = []
        for pattern in patterns:
            for match in re.finditer(pattern, user_input):
                # 根据模式调整分组顺序
                if '需要' in pattern or '要' in pattern:
                    qty_str = match.group(1)
                    model = match.group(2).strip()
                else:
                    model = match.group(1).strip()
                    qty_str = match.group(2)
                
                # 只提取数字型号（3-4 位）
                if re.match(r'^\d{3,4}$', model):
                    qty = parse_qty(qty_str)
                    extracted.append((model, qty))
        
        # 去重
        extracted = list(set(extracted))
        
        print(f"  提取结果：{extracted}")
        
        # 验证
        if set(extracted) == set(expected):
            print(f"  ✅ 正确")
        elif len(extracted) > 0:
            print(f"  ⚠️  部分正确")
        else:
            print(f"  ❌ 失败")
        
        print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_pattern_matching()
