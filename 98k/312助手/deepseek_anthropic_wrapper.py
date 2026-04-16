"""
DeepSeek to Anthropic API Wrapper

这个包装器将 DeepSeek API 伪装成 Anthropic API 格式
让 OpenClaw 可以直接使用 DeepSeek 而无需修改配置

API 兼容性:
- POST /v1/messages (Anthropic Messages API)
- GET /v1/models (Anthropic Models API)
"""

import os
import sys
import json
import time
import requests
from flask import Flask, request, jsonify, Response, make_response
from functools import wraps
import traceback
from flask_cors import CORS

# 导入 DeepSeek 配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.deepseek_config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_BASE,
    DEEPSEEK_MODEL,
    AI_TEMPERATURE,
    MAX_TOKENS,
    TIMEOUT
)

app = Flask(__name__)
CORS(app)  # 启用 CORS 支持

# Anthropic 兼容的模型映射
ANTHROPIC_TO_DEEPSEEK_MODELS = {
    # Claude 3 系列
    "claude-3-opus-20240229": "deepseek-chat",
    "claude-3-sonnet-20240229": "deepseek-chat",
    "claude-3-haiku-20240307": "deepseek-chat",
    # Claude 3.5 系列
    "claude-3-5-sonnet-20240620": "deepseek-chat",
    "claude-3-5-sonnet-20241022": "deepseek-chat",
    "claude-3-5-haiku-20241022": "deepseek-chat",
    # Claude 4 系列
    "claude-opus-4-6": "deepseek-chat",
    "claude-sonnet-4-20250514": "deepseek-chat",
    "claude-haiku-4-20250514": "deepseek-chat",
    # 默认
    "default": "deepseek-chat"
}


def anthropic_to_deepseek_message(anthropic_messages):
    """将 Anthropic 格式的消息转换为 DeepSeek 格式"""
    deepseek_messages = []
    
    for msg in anthropic_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # 处理内容数组
        if isinstance(content, list):
            text_content = ""
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_content += item.get("text", "")
                    elif item.get("type") == "image":
                        # DeepSeek 目前不支持图片，跳过
                        pass
            content = text_content
        
        # Anthropic 的 user/assistant → DeepSeek 的 user/assistant
        deepseek_messages.append({
            "role": role,
            "content": content
        })
    
    return deepseek_messages


def deepseek_to_anthropic_response(deepseek_response, model):
    """将 DeepSeek 响应转换为 Anthropic 格式"""
    try:
        choice = deepseek_response["choices"][0]
        message = choice["message"]
        usage = deepseek_response.get("usage", {})
        
        # 生成 Anthropic 格式的响应
        anthropic_response = {
            "id": f"msg_{deepseek_response.get('id', 'abc123')}",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": message.get("content", "")
                }
            ],
            "model": model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0)
            }
        }
        
        return anthropic_response
        
    except Exception as e:
        print(f"转换响应失败：{e}")
        return None


@app.before_request
def before_request():
    """请求前处理 - 记录日志和验证"""
    print(f"[{request.remote_addr}] {request.method} {request.path}")
    if request.method in ['POST', 'PUT'] and request.path.startswith('/v1/'):
        print(f"Headers: {dict(request.headers)}")
        print(f"Content-Length: {request.content_length}")
        api_key = request.headers.get('X-Api-Key') or request.headers.get('Authorization')
        if api_key:
            print(f"API Key: {api_key[:20]}...")

@app.route('/v1/messages', methods=['POST', 'OPTIONS'])
def messages():
    """
    Anthropic Messages API 兼容接口
    
    请求格式 (Anthropic):
    {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "你好"}
        ]
    }
    
    响应格式 (Anthropic):
    {
        "id": "msg_xxx",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "..."}],
        "model": "claude-3-opus-20240229",
        "usage": {...}
    }
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Api-Key')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "请求体必须是 JSON"
                }
            }), 400
        
        # 提取参数
        anthropic_model = data.get('model', 'claude-3-opus-20240229')
        max_tokens = data.get('max_tokens', MAX_TOKENS)
        messages = data.get('messages', [])
        system = data.get('system', '')
        
        # 模型映射
        deepseek_model = ANTHROPIC_TO_DEEPSEEK_MODELS.get(
            anthropic_model, 
            ANTHROPIC_TO_DEEPSEEK_MODELS['default']
        )
        
        # 转换消息格式
        deepseek_messages = []
        
        # 添加 system message（如果有）
        if system:
            deepseek_messages.append({
                "role": "system",
                "content": system
            })
        
        # 转换用户消息
        deepseek_messages.extend(anthropic_to_deepseek_message(messages))
        
        # 调用 DeepSeek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": deepseek_model,
            "messages": deepseek_messages,
            "temperature": AI_TEMPERATURE,
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            f"{DEEPSEEK_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        
        response.raise_for_status()
        deepseek_result = response.json()
        
        # 转换为 Anthropic 格式
        anthropic_result = deepseek_to_anthropic_response(deepseek_result, anthropic_model)
        
        if anthropic_result:
            return jsonify(anthropic_result)
        else:
            return jsonify({
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": "转换响应失败"
                }
            }), 500
        
    except requests.exceptions.Timeout:
        return jsonify({
            "type": "error",
            "error": {
                "type": "api_error",
                "message": "请求超时"
            }
        }), 504
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "type": "error",
            "error": {
                "type": "api_error",
                "message": f"API 请求失败：{str(e)}"
            }
        }), 500
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "type": "error",
            "error": {
                "type": "internal_server_error",
                "message": f"服务器错误：{str(e)}"
            }
        }), 500


@app.route('/v1/models', methods=['GET'])
def list_models():
    """
    Anthropic Models API 兼容接口
    
    返回可用的模型列表
    """
    models = [
        {"id": "claude-3-opus-20240229", "object": "model", "created": 1709251200, "owned_by": "anthropic"},
        {"id": "claude-3-sonnet-20240229", "object": "model", "created": 1709251200, "owned_by": "anthropic"},
        {"id": "claude-3-haiku-20240307", "object": "model", "created": 1709251200, "owned_by": "anthropic"},
        {"id": "claude-3-5-sonnet-20240620", "object": "model", "created": 1718841600, "owned_by": "anthropic"},
        {"id": "claude-3-5-sonnet-20241022", "object": "model", "created": 1729555200, "owned_by": "anthropic"},
        {"id": "claude-3-5-haiku-20241022", "object": "model", "created": 1729555200, "owned_by": "anthropic"},
        {"id": "claude-opus-4-6", "object": "model", "created": 1715040000, "owned_by": "anthropic"},
        {"id": "claude-sonnet-4-20250514", "object": "model", "created": 1747200000, "owned_by": "anthropic"},
        {"id": "claude-haiku-4-20250514", "object": "model", "created": 1747200000, "owned_by": "anthropic"},
    ]
    
    return jsonify({
        "object": "list",
        "data": models
    })


@app.route('/v1/models/<model_id>', methods=['GET'])
def get_model(model_id):
    """
    获取单个模型信息
    """
    return jsonify({
        "id": model_id,
        "object": "model",
        "created": 1709251200,
        "owned_by": "anthropic"
    })


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "service": "DeepSeek to Anthropic Wrapper",
        "version": "1.0.0"
    })


# 错误处理器
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "type": "error",
        "error": {
            "type": "not_found_error",
            "message": "请求的资源不存在"
        }
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "type": "error",
        "error": {
            "type": "internal_server_error",
            "message": "服务器内部错误"
        }
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("DeepSeek to Anthropic API Wrapper 启动中...")
    print("=" * 60)
    print(f"DeepSeek API: {DEEPSEEK_API_BASE}")
    print(f"使用模型：{DEEPSEEK_MODEL}")
    print(f"监听端口：5002")
    print("=" * 60)
    print("Anthropic 兼容接口:")
    print("  POST /v1/messages - Messages API")
    print("  GET  /v1/models   - Models API")
    print("=" * 60)
    print("\nOpenClaw 配置:")
    print("  设置 API Base URL: http://127.0.0.1:5002/v1")
    print("  Provider: anthropic")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=5002, debug=False)
