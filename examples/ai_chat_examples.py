# -*- coding: utf-8 -*-
"""
XCAGI AI 对话系统使用示例

展示如何使用 AI 对话系统的各种功能
"""

import requests
import json

# API 基础 URL
BASE_URL = "http://localhost:5000/api/ai"


def test_chat():
    """测试聊天功能"""
    print("=" * 60)
    print("测试聊天功能")
    print("=" * 60)
    
    # 测试用例
    test_messages = [
        "你好",
        "生成发货单",
        "客户列表",
        "不要上传文件",
        "再见",
    ]
    
    for message in test_messages:
        print(f"\n发送消息：{message}")
        
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": message,
                "user_id": "test_user"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"回复：{result['data']['text'][:100]}...")
            print(f"动作：{result['data']['action']}")
            if result['data'].get('data', {}).get('intent'):
                intent = result['data']['data']['intent']
                print(f"意图：{intent.get('primary_intent')}")
                print(f"工具：{intent.get('tool_key')}")
                print(f"否定：{intent.get('is_negated')}")
        else:
            print(f"错误：{response.text}")
        
        print("-" * 60)


def test_intent_recognition():
    """测试意图识别"""
    print("\n" + "=" * 60)
    print("测试意图识别")
    print("=" * 60)
    
    test_messages = [
        "生成发货单",
        "不要打印标签",
        "查看客户列表",
        "你好",
    ]
    
    for message in test_messages:
        print(f"\n消息：{message}")
        
        response = requests.post(
            f"{BASE_URL}/intent/test",
            json={"message": message}
        )
        
        if response.status_code == 200:
            result = response.json()
            data = result['data']
            print(f"  主意图：{data.get('primary_intent')}")
            print(f"  工具 Key: {data.get('tool_key')}")
            print(f"  是否问候：{data.get('is_greeting')}")
            print(f"  是否告别：{data.get('is_goodbye')}")
            print(f"  是否否定：{data.get('is_negated')}")
            print(f"  意图提示：{data.get('intent_hints')}")
        else:
            print(f"错误：{response.text}")
        
        print("-" * 60)


def test_context():
    """测试上下文管理"""
    print("\n" + "=" * 60)
    print("测试上下文管理")
    print("=" * 60)
    
    user_id = "test_user"
    
    # 发送多条消息
    messages = ["你好", "我想生成发货单", "谢谢"]
    
    for message in messages:
        print(f"\n发送：{message}")
        requests.post(
            f"{BASE_URL}/chat",
            json={"message": message, "user_id": user_id}
        )
    
    # 获取上下文
    print("\n获取对话上下文...")
    response = requests.get(
        f"{BASE_URL}/context",
        params={"user_id": user_id}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result['data']:
            history = result['data'].get('conversation_history', [])
            print(f"对话历史条数：{len(history)}")
            for i, msg in enumerate(history[-3:], 1):
                print(f"  {i}. [{msg['role']}] {msg['content'][:50]}")
        else:
            print("未找到上下文")
    
    # 清除上下文
    print("\n清除上下文...")
    response = requests.post(
        f"{BASE_URL}/context/clear",
        json={"user_id": user_id}
    )
    
    if response.status_code == 200:
        print("上下文已清除")
    
    print("-" * 60)


def test_config():
    """测试配置接口"""
    print("\n" + "=" * 60)
    print("测试配置接口")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/config")
    
    if response.status_code == 200:
        result = response.json()
        data = result['data']
        print(f"API 已配置：{data.get('api_configured')}")
        print(f"模型：{data.get('model')}")
        print(f"功能列表:")
        for feature in data.get('features', []):
            print(f"  - {feature}")
    
    print("-" * 60)


def test_health():
    """测试健康检查"""
    print("\n" + "=" * 60)
    print("测试健康检查")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/test")
    
    if response.status_code == 200:
        result = response.json()
        print(f"状态：{result['message']}")
        print(f"时间戳：{result.get('timestamp')}")
    
    print("-" * 60)


def main():
    """运行所有示例"""
    print("\nXCAGI AI 对话系统使用示例\n")
    
    try:
        # 测试健康检查
        test_health()
        
        # 测试配置
        test_config()
        
        # 测试意图识别
        test_intent_recognition()
        
        # 测试聊天功能
        test_chat()
        
        # 测试上下文管理
        test_context()
        
        print("\n✅ 所有示例运行完成!\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务器")
        print("请确保 Flask 应用正在运行：python -m flask run")
        print("\n启动命令:")
        print("  cd e:\\FHD\\XCAGI")
        print("  set DEEPSEEK_API_KEY=your_api_key")
        print("  python -m flask run\n")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")


if __name__ == "__main__":
    main()
