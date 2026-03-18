#!/usr/bin/env python3
# 测试生成发货单功能

import requests
import json

def test_generate_shipment():
    """测试生成发货单功能"""
    print("=== 测试生成发货单功能 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试数据
    test_data = {
        "order_text": "蕊芯一桶，24-4-8规格25",
        "template_name": "尹玉华1.xlsx",
        "custom_mode": False,
        "number_mode": True
    }
    
    try:
        # 测试 /api/generate 端点
        print(f"测试API端点: {base_url}/api/generate")
        print(f"请求数据: {test_data}")
        
        response = requests.post(
            f"{base_url}/api/generate",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30  # 增加超时时间，因为生成文档可能需要时间
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容:")
        
        try:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("success"):
                print("\n✅ 发货单生成成功")
                document = result.get("document", {})
                if document:
                    print(f"文件路径: {document.get('filepath', 'N/A')}")
                    print(f"文件名: {document.get('filename', 'N/A')}")
            else:
                print(f"❌ 发货单生成失败: {result.get('message', 'Unknown error')}")
                
        except json.JSONDecodeError:
            print(f"❌ JSON解析失败，原始响应: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
    except Exception as e:
        print(f"❌ 未知错误: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_generate_shipment()