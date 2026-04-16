"""
销售合同意图识别和槽位提取测试（真实业务逻辑版）

业务流程：
1. 识别客户名称
2. 查询该客户的历史订单/合同
3. 从历史订单中获取该客户购买过的产品列表
4. 匹配用户说的产品型号和数量
"""

import re


def test_with_customer_history():
    """基于客户历史订单的意图识别测试"""
    
    print("=" * 80)
    print("销售合同意图识别和槽位提取测试（真实业务逻辑）")
    print("=" * 80)
    print()
    
    # 模拟数据库数据
    customers_db = {
        "深圳市百木鼎家具有限公司": {
            "history_products": ["3721", "308", "9803"],  # 历史购买过的产品
        },
        "广东华天家具有限公司": {
            "history_products": ["9803", "779", "3721", "308"],
        },
        "七彩乐园": {
            "history_products": ["9803", "308", "3721"],
        },
    }
    
    # 测试用例
    test_cases = [
        {
            "input": "帮我打印销售合同客户名称是深圳市百木鼎家具有限公司，编号 3721 要三桶",
            "expected_customer": "深圳市百木鼎家具有限公司",
            "expected_products": ["3721"],
            "expected_quantities": {"3721": 3},
        },
        {
            "input": "打印一下深圳市百木鼎家具有限公司的销售合同需要两桶 3721 和一桶 308",
            "expected_customer": "深圳市百木鼎家具有限公司",
            "expected_products": ["3721", "308"],
            "expected_quantities": {"3721": 2, "308": 1},
        },
        {
            "input": "广东华天家具有限公司要 5 桶 9803，3 桶 779，还有 2 桶 3721",
            "expected_customer": "广东华天家具有限公司",
            "expected_products": ["9803", "779", "3721"],
            "expected_quantities": {"9803": 5, "779": 3, "3721": 2},
        },
        {
            "input": "七彩乐园那个单，9803 来 10 桶，308 来 5 桶",
            "expected_customer": "七彩乐园",
            "expected_products": ["9803", "308"],
            "expected_quantities": {"9803": 10, "308": 5},
        },
    ]
    
    # 多模式正则表达式（产品提取）
    product_patterns = [
        # 编号 3721 要三桶
        r'编号\s*(\d{3,4})\s*[要 x×]\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
        # 需要两桶 3721
        r'(?:需要 | 要)\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\d{3,4})',
        # 两桶 3721
        r'(\d+|[一二二三两三四五六七八九十百]+)\s*桶\s*(\d{3,4})',
        # 3721 两桶
        r'(\d{3,4})\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
        # 9803 来 10 桶（支持"来"等动词）
        r'(\d{3,4})\s*(?:来 | 要 | 订|订)\s*(\d+|[一二二三两三四五六七八九十百]+)\s*桶',
    ]
    
    # 中文字符数字映射（增强版）
    chinese_num = {
        "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, 
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "二十": 20, "三十": 30, "四十": 40, "五十": 50,
        "百": 100
    }
    
    def parse_qty(s: str) -> int:
        """解析数量（支持中文数字）"""
        s = s.strip()
        try:
            return int(s)
        except ValueError:
            # 尝试匹配中文数字
            if s in chinese_num:
                return chinese_num[s]
            # 尝试组合数字（如"三十二"）
            if "十" in s:
                parts = s.split("十")
                if len(parts) == 2:
                    tens = chinese_num.get(parts[0], 1) if parts[0] else 1
                    ones = chinese_num.get(parts[1], 0) if parts[1] else 0
                    return tens * 10 + ones
            return 1
    
    def extract_customer_name(text: str) -> str | None:
        """从文本中提取客户名称"""
        for customer in customers_db.keys():
            if customer in text:
                return customer
        return None
    
    def validate_product(customer: str, product: str) -> bool:
        """验证产品是否是该客户购买过的"""
        if customer not in customers_db:
            return True  # 未知客户，默认允许
        return product in customers_db[customer]["history_products"]
    
    # 运行测试
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['input']}")
        print(f"  期望客户：{test_case['expected_customer']}")
        print(f"  期望产品：{test_case['expected_products']}")
        print(f"  期望数量：{test_case['expected_quantities']}")
        
        # Step 1: 识别客户名称
        customer = extract_customer_name(test_case['input'])
        print(f"  识别客户：{customer}")
        
        if not customer:
            print(f"  ❌ 客户识别失败")
            print()
            continue
        
        # Step 2: 提取产品型号和数量
        extracted_products = []
        extracted_quantities = {}
        
        for pattern in product_patterns:
            for match in re.finditer(pattern, test_case['input']):
                # 模式 1: 编号 3721 要三桶 -> group(1)=产品，group(2)=数量
                # 其他模式需要判断
                if pattern.startswith('编号'):
                    # 编号 3721 要三桶
                    model = match.group(1).strip()
                    qty_str = match.group(2)
                elif '需要' in pattern or '要' in pattern:
                    # 检查"需要/要"是否在"桶"之前
                    need_pos = pattern.find('需要') if '需要' in pattern else pattern.find('要')
                    tong_pos = pattern.find('桶')
                    if need_pos >= 0 and need_pos < tong_pos:
                        # 数量在前：需要两桶 3721
                        qty_str = match.group(1)
                        model = match.group(2).strip()
                    else:
                        # 产品在前：3721 要两桶
                        model = match.group(1).strip()
                        qty_str = match.group(2)
                elif '来' in pattern:
                    # "来"的模式：9803 来 10 桶
                    model = match.group(1).strip()
                    qty_str = match.group(2)
                else:
                    # 其他模式：产品在前
                    model = match.group(1).strip()
                    qty_str = match.group(2)
                
                # 验证产品是否是该客户购买过的
                qty = parse_qty(qty_str)
                is_valid = validate_product(customer, model)
                print(f"    匹配到产品：{model}, 数量：{qty_str} ({qty}), 验证：{'✅' if is_valid else '❌'}")
                
                if is_valid:
                    extracted_products.append(model)
                    extracted_quantities[model] = qty
        
        # 去重
        extracted_products = list(set(extracted_products))
        
        print(f"  提取结果：")
        print(f"    产品：{extracted_products}")
        print(f"    数量：{extracted_quantities}")
        
        # 验证
        if set(extracted_products) == set(test_case['expected_products']) and \
           extracted_quantities == test_case['expected_quantities']:
            print(f"  ✅ 完全正确")
        elif len(extracted_products) > 0:
            print(f"  ⚠️  部分正确")
        else:
            print(f"  ❌ 失败")
        
        print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_with_customer_history()
