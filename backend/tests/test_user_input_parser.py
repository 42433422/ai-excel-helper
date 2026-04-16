"""测试用户输入解析器的产品识别功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_input_parser import parse_user_input


def test_product_extraction():
    """测试产品型号和数量的提取"""
    
    # 测试用例 1: 原格式 (应该仍然有效)
    text1 = "帮我打印销售合同客户是深圳市百木鼎家具有限公司，编号 3721 要三桶"
    result1 = parse_user_input(text1)
    print(f"测试 1: {text1}")
    print(f"客户：{result1['customer_name']}")
    print(f"产品：{result1['products']}")
    print(f"数量：{result1['quantities']}")
    print()
    
    # 测试用例 2: 新格式 (需要两桶 3721)
    text2 = "打印一下深圳市百木鼎家具有限公司的销售合同需要两桶 3721 和一桶 308"
    result2 = parse_user_input(text2)
    print(f"测试 2: {text2}")
    print(f"客户：{result2['customer_name']}")
    print(f"产品：{result2['products']}")
    print(f"数量：{result2['quantities']}")
    print()
    
    # 测试用例 3: 简单格式 (两桶 3721)
    text3 = "销售合同 两桶 3721 一桶 308"
    result3 = parse_user_input(text3)
    print(f"测试 3: {text3}")
    print(f"客户：{result3['customer_name']}")
    print(f"产品：{result3['products']}")
    print(f"数量：{result3['quantities']}")
    print()
    
    # 测试用例 4: 产品在前 (3721 两桶)
    text4 = "3721 两桶，308 一桶"
    result4 = parse_user_input(text4)
    print(f"测试 4: {text4}")
    print(f"客户：{result4['customer_name']}")
    print(f"产品：{result4['products']}")
    print(f"数量：{result4['quantities']}")
    print()
    
    # 测试用例 5: 混合格式
    text5 = "深圳市百木鼎家具有限公司 编号 3721 要三桶，还需要两桶 308"
    result5 = parse_user_input(text5)
    print(f"测试 5: {text5}")
    print(f"客户：{result5['customer_name']}")
    print(f"产品：{result5['products']}")
    print(f"数量：{result5['quantities']}")
    print()


if __name__ == "__main__":
    test_product_extraction()
