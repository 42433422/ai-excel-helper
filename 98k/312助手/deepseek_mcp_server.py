"""
DeepSeek MCP Server - 为 OpenClaw 提供 DeepSeek API 服务

这个服务器作为 OpenClaw 和 DeepSeek API 之间的桥梁，提供以下功能：
1. HTTP API 接口，兼容 OpenClaw 的调用格式
2. DeepSeek 对话能力
3. 支持读取 Excel 等工具函数
4. 智能意图识别和任务分发

使用方法：
    python deepseek_mcp_server.py
    
启动后，服务器会监听 http://127.0.0.1:5001
OpenClaw 可以通过 HTTP 请求调用 DeepSeek 功能
"""

import os
import sys
import json
import requests
from flask import Flask, request, jsonify
from functools import wraps
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置
from config.deepseek_config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_BASE,
    DEEPSEEK_MODEL,
    AI_TEMPERATURE,
    MAX_TOKENS,
    TIMEOUT,
    OPENCLAW_API_PORT
)

app = Flask(__name__)

# ==================== 工具函数定义 ====================

def read_excel_file(file_path, sheet_name=None):
    """读取 Excel 文件内容"""
    try:
        import pandas as pd
        
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            # 读取所有 sheet
            excel_file = pd.ExcelFile(file_path)
            result = {}
            for sheet in excel_file.sheet_names:
                result[sheet] = pd.read_excel(file_path, sheet_name=sheet).to_dict('records')
            return result
        
        return df.to_dict('records')
    except Exception as e:
        return {"error": str(e)}


def search_products(keyword):
    """搜索产品信息"""
    try:
        # 这里可以连接数据库查询产品
        # 简化版本返回示例数据
        return {
            "products": [
                {"name": "示例产品 1", "model": "A001", "price": 100},
                {"name": "示例产品 2", "model": "A002", "price": 200}
            ]
        }
    except Exception as e:
        return {"error": str(e)}


def get_customers():
    """获取客户列表"""
    try:
        # 这里可以连接数据库查询客户
        return {
            "customers": [
                {"name": "客户 A", "contact": "张三", "phone": "13800138000"},
                {"name": "客户 B", "contact": "李四", "phone": "13900139000"}
            ]
        }
    except Exception as e:
        return {"error": str(e)}


def get_shipments(customer_name=None, date_range=None):
    """查询出货单记录"""
    try:
        # 这里可以连接数据库查询出货单
        return {
            "shipments": [
                {"id": "SH001", "customer": "客户 A", "date": "2026-03-10", "total": 1000},
                {"id": "SH002", "customer": "客户 B", "date": "2026-03-11", "total": 2000}
            ]
        }
    except Exception as e:
        return {"error": str(e)}


# 工具注册表
TOOLS_REGISTRY = {
    "read_excel": {
        "name": "read_excel",
        "description": "读取 Excel 文件内容",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Excel 文件路径"},
                "sheet_name": {"type": "string", "description": "工作表名称（可选）"}
            },
            "required": ["file_path"]
        },
        "function": read_excel_file
    },
    "search_products": {
        "name": "search_products",
        "description": "搜索产品信息",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["keyword"]
        },
        "function": search_products
    },
    "get_customers": {
        "name": "get_customers",
        "description": "获取客户列表",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "function": get_customers
    },
    "get_shipments": {
        "name": "get_shipments",
        "description": "查询出货单记录",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "客户名称"},
                "date_range": {"type": "string", "description": "日期范围"}
            },
            "required": []
        },
        "function": get_shipments
    }
}


# ==================== DeepSeek API 调用 ====================

def call_deepseek(messages, tools=None):
    """
    调用 DeepSeek API 进行对话
    
    Args:
        messages: 对话消息列表
        tools: 可选的工具列表
    
    Returns:
        dict: API 响应结果
    """
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": AI_TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
        
        # 如果提供了工具，添加到请求中
        if tools:
            payload["tools"] = tools
        
        response = requests.post(
            f"{DEEPSEEK_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        
        response.raise_for_status()
        result = response.json()
        
        return {
            "success": True,
            "data": result,
            "usage": result.get("usage", {})
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时，请重试"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API 请求失败：{str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"调用 DeepSeek 失败：{str(e)}"
        }


# ==================== HTTP API 路由 ====================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "service": "DeepSeek MCP Server",
        "version": "1.0.0"
    })


@app.route('/chat', methods=['POST'])
def chat():
    """
    智能对话接口 - OpenClaw 兼容格式
    
    请求格式：
    {
        "message": "用户消息",
        "conversation_id": "会话 ID（可选）",
        "use_tools": true  # 是否使用工具
    }
    
    响应格式：
    {
        "reply": "AI 回复",
        "conversation_id": "会话 ID",
        "usage": {...}
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "error": "缺少必要参数：message"
            }), 400
        
        user_message = data['message']
        conversation_id = data.get('conversation_id', 'default')
        use_tools = data.get('use_tools', True)
        
        # 构建消息历史
        messages = [
            {
                "role": "system",
                "content": """你是一个智能助手，可以帮助用户查询产品信息、出货单、客户信息等。
你可以使用以下工具：
1. read_excel - 读取 Excel 文件
2. search_products - 搜索产品
3. get_customers - 获取客户列表
4. get_shipments - 查询出货单

请根据用户的问题，智能选择合适的工具来帮助用户。"""
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
        
        # 准备工具定义（如果需要）
        tools = None
        if use_tools:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["parameters"]
                    }
                }
                for tool in TOOLS_REGISTRY.values()
            ]
        
        # 调用 DeepSeek
        result = call_deepseek(messages, tools=tools)
        
        if not result["success"]:
            return jsonify({
                "error": result["error"]
            }), 500
        
        # 检查是否需要调用工具
        response_data = result["data"]
        choice = response_data["choices"][0]
        message = choice["message"]
        
        # 如果有工具调用
        if message.get("tool_calls"):
            tool_calls = message["tool_calls"]
            tool_results = []
            
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                
                # 执行工具函数
                if function_name in TOOLS_REGISTRY:
                    tool_func = TOOLS_REGISTRY[function_name]["function"]
                    try:
                        tool_result = tool_func(**function_args)
                        tool_results.append({
                            "tool": function_name,
                            "result": tool_result
                        })
                    except Exception as e:
                        tool_results.append({
                            "tool": function_name,
                            "error": str(e)
                        })
            
            # 如果有工具结果，再次调用 DeepSeek 获取最终回复
            if tool_results:
                messages.append(message)
                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_results, ensure_ascii=False)
                })
                
                result = call_deepseek(messages)
                if result["success"]:
                    response_data = result["data"]
                    message = response_data["choices"][0]["message"]
        
        # 返回回复
        return jsonify({
            "reply": message["content"],
            "conversation_id": conversation_id,
            "usage": result.get("usage", {})
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": f"服务器错误：{str(e)}"
        }), 500


@app.route('/completions', methods=['POST'])
def completions():
    """
    标准 OpenAI 兼容接口
    
    请求格式：
    {
        "model": "deepseek-chat",
        "messages": [...],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'messages' not in data:
            return jsonify({
                "error": "缺少必要参数：messages"
            }), 400
        
        # 使用用户提供的参数或默认值
        model = data.get('model', DEEPSEEK_MODEL)
        messages = data['messages']
        temperature = data.get('temperature', AI_TEMPERATURE)
        max_tokens = data.get('max_tokens', MAX_TOKENS)
        tools = data.get('tools')
        
        # 调用 DeepSeek
        result = call_deepseek(messages, tools=tools)
        
        if not result["success"]:
            return jsonify({
                "error": result["error"]
            }), 500
        
        return jsonify(result["data"])
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": f"服务器错误：{str(e)}"
        }), 500


@app.route('/tools', methods=['GET'])
def list_tools():
    """获取可用工具列表"""
    return jsonify({
        "tools": list(TOOLS_REGISTRY.values())
    })


@app.route('/tools/<tool_name>', methods=['POST'])
def call_tool(tool_name):
    """
    直接调用工具
    
    请求格式：
    {
        "parameters": {...}
    }
    """
    try:
        if tool_name not in TOOLS_REGISTRY:
            return jsonify({
                "error": f"未知工具：{tool_name}"
            }), 404
        
        data = request.get_json() or {}
        parameters = data.get('parameters', {})
        
        tool_func = TOOLS_REGISTRY[tool_name]["function"]
        result = tool_func(**parameters)
        
        return jsonify({
            "tool": tool_name,
            "result": result
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": f"工具调用失败：{str(e)}"
        }), 500


# ==================== 主程序 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("DeepSeek MCP Server 启动中...")
    print("=" * 60)
    print(f"API 密钥：{'已配置' if DEEPSEEK_API_KEY else '未配置'}")
    print(f"API 地址：{DEEPSEEK_API_BASE}")
    print(f"使用模型：{DEEPSEEK_MODEL}")
    print(f"监听端口：{OPENCLAW_API_PORT}")
    print("=" * 60)
    print("OpenClaw 可以通过以下地址调用：")
    print(f"  对话接口：http://127.0.0.1:{OPENCLAW_API_PORT}/chat")
    print(f"  标准接口：http://127.0.0.1:{OPENCLAW_API_PORT}/completions")
    print(f"  健康检查：http://127.0.0.1:{OPENCLAW_API_PORT}/health")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=OPENCLAW_API_PORT, debug=False)
