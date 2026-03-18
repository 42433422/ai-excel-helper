#!/usr/bin/env python3
# 调试正则表达式关键词提取

import re

def debug_regex():
    """调试正则表达式关键词提取"""
    print("=== 调试正则表达式关键词提取 ===")
    
    test_text = "24-4-8规格25"
    print(f"测试文本: '{test_text}'")
    
    # 当前使用的正则表达式
    pattern1 = r'[a-zA-Z0-9\-]+'
    matches1 = re.findall(pattern1, test_text)
    print(f"当前正则表达式 '{pattern1}' 匹配结果: {matches1}")
    
    # 改进的正则表达式
    pattern2 = r'[a-zA-Z0-9\-]+'
    matches2 = re.findall(pattern2, test_text)
    print(f"改进正则表达式 '{pattern2}' 匹配结果: {matches2}")
    
    # 更宽松的正则表达式
    pattern3 = r'[a-zA-Z0-9\-\*]+'
    matches3 = re.findall(pattern3, test_text)
    print(f"宽松正则表达式 '{pattern3}' 匹配结果: {matches3}")
    
    # 测试"24-4-8*"
    test_text2 = "24-4-8*"
    print(f"\n测试文本2: '{test_text2}'")
    print(f"当前正则表达式 '{pattern1}' 匹配结果: {re.findall(pattern1, test_text2)}")
    print(f"宽松正则表达式 '{pattern3}' 匹配结果: {re.findall(pattern3, test_text2)}")
    
    # 检查实际的AI解析器如何处理
    print("\n=== 模拟AI解析器的处理过程 ===")
    
    # 模拟AI解析器中可能的处理
    # AI解析器可能有不同的正则表达式
    ai_pattern = r'[0-9a-zA-Z\-]+'
    ai_matches = re.findall(ai_pattern, test_text)
    print(f"AI解析器可能使用的正则表达式 '{ai_pattern}' 匹配结果: {ai_matches}")
    
    # 检查是否包含星号的情况
    test_text_with_star = "24-4-8*"
    ai_matches_star = re.findall(ai_pattern, test_text_with_star)
    print(f"带星号的测试文本 '{test_text_with_star}' 匹配结果: {ai_matches_star}")

if __name__ == "__main__":
    debug_regex()