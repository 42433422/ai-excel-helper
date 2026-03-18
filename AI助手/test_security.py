#!/usr/bin/env python3
# 测试数据库操作安全性
import requests
import json

BASE_URL = 'http://localhost:5000/api'

def test_sql_injection():
    """测试SQL注入防护"""
    print('=== 测试SQL注入防护 ===')
    
    # 测试添加产品的SQL注入
    test_payloads = [
        # 基本注入尝试
        {"model_number":"'; DROP TABLE products; --", "name":"测试注入", "price":99.99, "unit":"七彩乐园"},
        # 引号转义测试
        {"model_number":"O'Conner", "name":"测试引号", "price":199.99, "unit":"七彩乐园"},
        # 特殊字符测试
        {"model_number":"test-123;--", "name":"测试特殊字符", "price":299.99, "unit":"七彩乐园"}
    ]
    
    for i, payload in enumerate(test_payloads):
        print(f'\n测试 {i+1}: {payload["name"]}')
        print(f'  型号: {payload["model_number"]}')
        
        try:
            response = requests.post(
                f'{BASE_URL}/products',
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload)
            )
            
            result = response.json()
            print(f'  状态码: {response.status_code}')
            print(f'  成功: {result.get("success", False)}')
            print(f'  消息: {result.get("message", "无消息")}')
            
        except Exception as e:
            print(f'  错误: {e}')

def test_input_validation():
    """测试输入验证"""
    print('\n=== 测试输入验证 ===')
    
    # 测试缺少必需字段
    missing_fields = {
        "name":"测试产品",
        "price":99.99,
        "unit":"七彩乐园"
        # 缺少model_number
    }
    
    print('测试缺少必需字段 (model_number):')
    try:
        response = requests.post(
            f'{BASE_URL}/products',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(missing_fields)
        )
        
        result = response.json()
        print(f'  状态码: {response.status_code}')
        print(f'  成功: {result.get("success", False)}')
        print(f'  消息: {result.get("message", "无消息")}')
        
    except Exception as e:
        print(f'  错误: {e}')

def test_unit_database_validation():
    """测试单位数据库验证"""
    print('\n=== 测试单位数据库验证 ===')
    
    # 测试不存在的单位
    non_existent_unit = {
        "model_number":"TEST404",
        "name":"测试不存在的单位",
        "price":99.99,
        "unit":"不存在的单位12345"
    }
    
    print('测试不存在的单位:')
    try:
        response = requests.post(
            f'{BASE_URL}/products',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(non_existent_unit)
        )
        
        result = response.json()
        print(f'  状态码: {response.status_code}')
        print(f'  成功: {result.get("success", False)}')
        print(f'  消息: {result.get("message", "无消息")}')
        
    except Exception as e:
        print(f'  错误: {e}')

if __name__ == '__main__':
    print('开始数据库操作安全性测试...\n')
    
    test_sql_injection()
    test_input_validation()
    test_unit_database_validation()
    
    print('\n=== 测试完成 ===')
    print('所有测试都应该返回适当的错误消息，而不是服务器崩溃。')