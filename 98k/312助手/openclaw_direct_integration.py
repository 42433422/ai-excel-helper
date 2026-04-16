"""
OpenClaw + DeepSeek 直接集成方案

由于 OpenClaw Gateway 需要加密的认证令牌，我们创建一个更简单的方案：
直接在 OpenClaw 的 Canvas 中使用 HTTP 请求节点调用 DeepSeek MCP Server
"""

import requests
import json

# DeepSeek MCP Server 配置
DEEPSEEK_SERVER = "http://127.0.0.1:5001"

def test_deepseek_connection():
    """测试 DeepSeek 连接"""
    try:
        response = requests.get(f"{DEEPSEEK_SERVER}/health", timeout=5)
        if response.status_code == 200:
            print("✅ DeepSeek MCP Server 连接正常")
            print(f"响应：{response.json()}")
            return True
        else:
            print(f"❌ DeepSeek MCP Server 响应异常：{response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到 DeepSeek MCP Server: {e}")
        return False


def chat_with_deepseek(message, use_tools=True):
    """
    直接与 DeepSeek 对话
    
    Args:
        message: 用户消息
        use_tools: 是否使用工具
    
    Returns:
        str: AI 回复
    """
    try:
        response = requests.post(
            f"{DEEPSEEK_SERVER}/chat",
            json={
                "message": message,
                "use_tools": use_tools
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            reply = result.get('reply', '没有回复')
            print(f"💬 DeepSeek 回复：{reply}")
            return reply
        else:
            print(f"❌ 请求失败：{response.status_code}")
            print(f"响应：{response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        return None


def main():
    """主函数 - 演示如何使用"""
    print("=" * 60)
    print("OpenClaw + DeepSeek 直接集成演示")
    print("=" * 60)
    
    # 测试连接
    if not test_deepseek_connection():
        print("\n请先启动 DeepSeek MCP Server:")
        print("  python deepseek_mcp_server.py")
        return
    
    print("\n" + "=" * 60)
    print("测试对话功能")
    print("=" * 60)
    
    # 测试 1：简单对话
    print("\n测试 1: 简单对话")
    chat_with_deepseek("你好，请介绍一下你自己", use_tools=False)
    
    # 测试 2：查询数据
    print("\n测试 2: 查询客户")
    chat_with_deepseek("帮我查询一下有哪些客户", use_tools=True)
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n在 OpenClaw Canvas 中配置:")
    print("1. 添加 HTTP Request 节点")
    print("2. URL: http://127.0.0.1:5001/chat")
    print("3. Method: POST")
    print("4. Headers: Content-Type: application/json")
    print("5. Body: {\"message\": \"{{user_input}}\", \"use_tools\": true}")
    print("6. 解析响应中的 reply 字段")


if __name__ == "__main__":
    main()
