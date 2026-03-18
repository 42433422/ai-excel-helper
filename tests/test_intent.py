# -*- coding: utf-8 -*-
"""
意图识别测试脚本

测试意图识别的准确率和功能完整性
"""

import sys
import os

# 直接导入意图服务模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    "intent_service",
    r"e:\FHD\XCAGI\app\services\intent_service.py"
)
intent_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intent_service)

recognize_intents = intent_service.recognize_intents
is_greeting = intent_service.is_greeting
is_goodbye = intent_service.is_goodbye
is_negation = intent_service.is_negation


def test_intent_recognition():
    """测试意图识别功能"""
    print("=" * 60)
    print("意图识别测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        # (输入消息，期望的主要意图，期望的工具 key)
        ("生成发货单", "shipment_generate", "shipment_generate"),
        ("我要开单", "shipment_generate", "shipment_generate"),
        ("不要生成发货单", "shipment_generate", None),  # 否定
        ("客户列表", "customers", "customers"),
        ("产品库", "products", "products"),
        ("上传 excel 文件", "upload_file", "upload_file"),
        ("不要上传", "upload_file", None),  # 否定
        ("你好", None, None),  # 问候
        ("再见", None, None),  # 告别
        ("发货单模板", "shipment_template", "shipment_template"),
        ("打印标签", "print_label", "print_label"),
        ("不要打印", "print_label", None),  # 否定
        ("查看出货记录", "shipments", "shipments"),
        ("原材料库存", "materials", "materials"),
        ("发微信给他", "wechat_send", "wechat_send"),
    ]
    
    correct_count = 0
    total_count = len(test_cases)
    
    for message, expected_intent, expected_tool in test_cases:
        result = recognize_intents(message)
        
        intent_match = result["primary_intent"] == expected_intent
        tool_match = result["tool_key"] == expected_tool
        
        # 检查特殊标志
        if "你好" in message or "你好" in message.lower():
            is_greeting_correct = result["is_greeting"] == True
            status = "✓" if is_greeting_correct else "✗"
            print(f"{status} '{message}' => 问候：{result['is_greeting']}")
            if is_greeting_correct:
                correct_count += 1
        elif "再见" in message or "拜拜" in message:
            is_goodbye_correct = result["is_goodbye"] == True
            status = "✓" if is_goodbye_correct else "✗"
            print(f"{status} '{message}' => 告别：{result['is_goodbye']}")
            if is_goodbye_correct:
                correct_count += 1
        else:
            status = "✓" if (intent_match and tool_match) else "✗"
            print(f"{status} '{message}' => 意图：{result['primary_intent']}, 工具：{result['tool_key']}, 否定：{result['is_negated']}")
            
            if intent_match and tool_match:
                correct_count += 1
    
    print("=" * 60)
    accuracy = correct_count / total_count * 100
    print(f"测试结果：{correct_count}/{total_count} 正确 ({accuracy:.1f}%)")
    print("=" * 60)
    
    return accuracy >= 90


def test_negation_detection():
    """测试否定检测功能"""
    print("\n" + "=" * 60)
    print("否定检测测试")
    print("=" * 60)
    
    test_cases = [
        ("不要生成发货单", True),
        ("别上传文件", True),
        ("不用打印", True),
        ("生成发货单", False),
        ("上传文件", False),
        ("我要开单", False),
    ]
    
    correct_count = 0
    for message, expected_negated in test_cases:
        result = recognize_intents(message)
        is_correct = result["is_negated"] == expected_negated
        
        status = "✓" if is_correct else "✗"
        print(f"{status} '{message}' => 否定：{result['is_negated']} (期望：{expected_negated})")
        
        if is_correct:
            correct_count += 1
    
    print("=" * 60)
    accuracy = correct_count / len(test_cases) * 100
    print(f"否定检测：{correct_count}/{len(test_cases)} 正确 ({accuracy:.1f}%)")
    print("=" * 60)
    
    return accuracy >= 90


def test_greeting_goodbye():
    """测试问候和告别检测"""
    print("\n" + "=" * 60)
    print("问候/告别检测测试")
    print("=" * 60)
    
    greeting_tests = [
        ("你好", True),
        ("您好", True),
        ("早上好", True),
        ("在吗", True),
        ("生成发货单", False),
    ]
    
    goodbye_tests = [
        ("再见", True),
        ("拜拜", True),
        ("先这样", True),
        ("没事了", True),
        ("生成发货单", False),
    ]
    
    correct_count = 0
    total_count = len(greeting_tests) + len(goodbye_tests)
    
    print("问候检测:")
    for message, expected in greeting_tests:
        result = is_greeting(message)
        is_correct = result == expected
        status = "✓" if is_correct else "✗"
        print(f"{status} '{message}' => {result} (期望：{expected})")
        if is_correct:
            correct_count += 1
    
    print("\n告别检测:")
    for message, expected in goodbye_tests:
        result = is_goodbye(message)
        is_correct = result == expected
        status = "✓" if is_correct else "✗"
        print(f"{status} '{message}' => {result} (期望：{expected})")
        if is_correct:
            correct_count += 1
    
    print("=" * 60)
    accuracy = correct_count / total_count * 100
    print(f"问候/告别检测：{correct_count}/{total_count} 正确 ({accuracy:.1f}%)")
    print("=" * 60)
    
    return accuracy >= 90


def main():
    """运行所有测试"""
    print("\nXCAGI AI 对话系统 - 意图识别测试\n")
    
    test1 = test_intent_recognition()
    test2 = test_negation_detection()
    test3 = test_greeting_goodbye()
    
    print("\n" + "=" * 60)
    print("总体测试结果")
    print("=" * 60)
    print(f"意图识别测试：{'通过 ✓' if test1 else '失败 ✗'}")
    print(f"否定检测测试：{'通过 ✓' if test2 else '失败 ✗'}")
    print(f"问候/告别检测：{'通过 ✓' if test3 else '失败 ✗'}")
    print("=" * 60)
    
    all_passed = test1 and test2 and test3
    if all_passed:
        print("\n🎉 所有测试通过！意图识别准确率 > 90%\n")
    else:
        print("\n⚠️ 部分测试未通过，请检查实现\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
