#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试服务状态
"""

import requests

def test_api():
    """测试API服务"""
    print("🔍 测试后端API服务...")
    try:
        response = requests.get('http://localhost:5000/api/customers', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API服务正常 - 获取到 {data['count']} 个客户")
            print("📋 前5个客户:")
            for i, customer in enumerate(data['customers'][:5]):
                print(f"   {i+1}. {customer['unit_name']}")
            return True
        else:
            print(f"❌ API返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API服务连接失败: {e}")
        return False

def test_frontend():
    """测试前端服务"""
    print("\n🔍 测试前端Web服务...")
    try:
        response = requests.get('http://localhost:8080/templates/database_management.html', timeout=5)
        if response.status_code == 200:
            print("✅ 前端Web服务正常 - 数据库管理页面可访问")
            return True
        else:
            print(f"❌ 前端服务返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 前端服务连接失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始测试数据库管理系统服务...\n")
    
    api_ok = test_api()
    frontend_ok = test_frontend()
    
    print("\n📊 服务状态总结:")
    print(f"后端API服务: {'✅ 正常' if api_ok else '❌ 异常'}")
    print(f"前端Web服务: {'✅ 正常' if frontend_ok else '❌ 异常'}")
    
    if api_ok and frontend_ok:
        print("\n🎉 所有服务正常运行！")
        print("📖 访问地址:")
        print("   - 数据库管理界面: http://localhost:8080/templates/database_management.html")
        print("   - 主界面: http://localhost:8080/index.html")
        print("   - API服务: http://localhost:5000")
    else:
        print("\n⚠️  部分服务异常，请检查服务状态")

if __name__ == "__main__":
    main()