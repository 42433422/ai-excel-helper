"""
销售合同意图识别和槽位提取测试

使用真实数据库数据测试多种用户表达方式
"""

import sys
import os
# 添加 backend 目录到路径
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from user_input_parser import extract_structured_info


def test_with_real_data():
    """使用真实数据测试意图识别"""
    
    print("=" * 80)
    print("销售合同意图识别和槽位提取测试")
    print("=" * 80)
    print()
    
    # 测试用例 1: 标准格式（带编号）
    test_case_1 = "帮我打印销售合同客户名称是深圳市百木鼎家具有限公司，编号 3721 要三桶"
    print(f"测试 1: {test_case_1}")
    result1 = extract_structured_info(test_case_1)
    print_result(result1)
    print()
    
    # 测试用例 2: 自然语言（需要两桶 XXX）
    test_case_2 = "打印一下深圳市百木鼎家具有限公司的销售合同需要两桶 3721 和一桶 308"
    print(f"测试 2: {test_case_2}")
    result2 = extract_structured_info(test_case_2)
    print_result(result2)
    print()
    
    # 测试用例 3: 简洁格式（直接说产品和数量）
    test_case_3 = "销售合同 两桶 3721 一桶 308"
    print(f"测试 3: {test_case_3}")
    result3 = extract_structured_info(test_case_3)
    print_result(result3)
    print()
    
    # 测试用例 4: 倒装格式（产品在前）
    test_case_4 = "3721 两桶，308 一桶"
    print(f"测试 4: {test_case_4}")
    result4 = extract_structured_info(test_case_4)
    print_result(result4)
    print()
    
    # 测试用例 5: 混合格式
    test_case_5 = "深圳市百木鼎家具有限公司 编号 3721 要三桶，还需要两桶 308"
    print(f"测试 5: {test_case_5}")
    result5 = extract_structured_info(test_case_5)
    print_result(result5)
    print()
    
    # 测试用例 6: 多产品复杂订单
    test_case_6 = "广东华天家具有限公司要 5 桶 9803，3 桶 779，还有 2 桶 3721"
    print(f"测试 6: {test_case_6}")
    result6 = extract_structured_info(test_case_6)
    print_result(result6)
    print()
    
    # 测试用例 7: 口语化表达
    test_case_7 = "七彩乐园那个单，9803 来 10 桶，308 来 5 桶"
    print(f"测试 7: {test_case_7}")
    result7 = extract_structured_info(test_case_7)
    print_result(result7)
    print()
    
    # 测试用例 8: 只有客户名（让 LLM 补充产品）
    test_case_8 = "深圳市百木鼎家具有限公司的销售合同"
    print(f"测试 8: {test_case_8}")
    result8 = extract_structured_info(test_case_8)
    print_result(result8)
    print()
    
    # 测试用例 9: 中文字符数字
    test_case_9 = "需要三十二桶 3721 和十五桶 308"
    print(f"测试 9: {test_case_9}")
    result9 = extract_structured_info(test_case_9)
    print_result(result9)
    print()
    
    # 测试用例 10: 极简表达
    test_case_10 = "3721 五桶"
    print(f"测试 10: {test_case_10}")
    result10 = extract_structured_info(test_case_10)
    print_result(result10)
    print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


def print_result(result: dict):
    """格式化输出结果"""
    print(f"  客户名称：{result.get('customer_name', '未识别')}")
    print(f"  产品列表：{result.get('products', [])}")
    print(f"  数量信息：{result.get('quantities', {})}")
    
    # 验证结果
    if result.get('products'):
        print(f"  ✅ 成功识别 {len(result['products'])} 个产品")
        for prod in result['products']:
            qty = result['quantities'].get(prod, '未知')
            print(f"     - {prod}: {qty} 桶")
    else:
        print(f"  ❌ 未识别到产品")


if __name__ == "__main__":
    test_with_real_data()
