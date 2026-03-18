# -*- coding: utf-8 -*-
"""
AI 聊天路由模块

提供 AI 聊天接口，包括：
- /api/ai/chat: 统一聊天接口
- 意图识别、工具调用、AI 兜底
- DeepSeek API 集成
"""

import os
import logging
import asyncio
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 创建蓝图
ai_chat_bp = Blueprint("ai_chat", __name__, url_prefix="/api/ai")


# 工具关键词映射（与意图层配合使用）
TOOL_KEYWORDS_MAP = {
    "shipment_generate": {
        "keywords": ["生成发货单", "发货单生成", "做发货单", "开发货单", "开单", "打单"],
        "priority": 12,
    },
    "shipment_template": {
        "keywords": ["发货单模板", "模板", "抬头", "购货单位", "联系人", "订单编号"],
        "priority": 9,
    },
    "excel_decompose": {
        "keywords": ["分解 excel", "解析 excel", "分解模板", "提取词条", "excel 模板"],
        "priority": 9,
    },
    "shipments": {
        "keywords": ["出货", "订单", "发货", "出货单", "发货记录", "订单列表"],
        "priority": 8,
    },
    "products": {
        "keywords": ["产品", "商品", "型号", "产品列表", "产品库", "规格"],
        "priority": 7,
    },
    "customers": {
        "keywords": ["客户", "顾客", "单位", "用户列表", "用户名单", "购买单位"],
        "priority": 6,
    },
    "print_label": {
        "keywords": ["打印", "标签", "打印标签", "商标导出", "标签导出"],
        "priority": 5,
    },
    "upload_file": {
        "keywords": ["上传", "导入", "解析", "上传文件", "导入文件", "上传 excel"],
        "priority": 5,
    },
    "materials": {
        "keywords": ["原材料", "材料", "库存", "原材料库存", "库存查询"],
        "priority": 4,
    },
}


def get_ai_service():
    """获取 AI 对话服务实例"""
    from app.services.ai_conversation_service import get_ai_conversation_service
    return get_ai_conversation_service()


def recognize_intents(message: str) -> Dict[str, Any]:
    """导入意图识别函数"""
    from app.services.intent_service import recognize_intents
    return recognize_intents(message)


@ai_chat_bp.route("/chat", methods=["POST"])
@swag_from({
    'summary': 'AI 聊天',
    'description': '统一 AI 聊天接口，支持意图识别和工具调用',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': '用户消息'},
                    'user_id': {'type': 'string', 'description': '用户 ID（可选）'},
                    'context': {'type': 'object', 'description': '额外上下文（可选）'}
                },
                'required': ['message']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'}
                }
            }
        }
    }
})
def chat():
    """
    AI 聊天接口
    
    请求格式：
    {
        "message": "用户消息",
        "user_id": "用户 ID（可选，默认使用 session）",
        "context": {}  # 额外上下文（可选）
    }
    
    响应格式：
    {
        "success": True/False,
        "message": "响应消息",
        "data": {
            "text": "AI 回复文本",
            "action": "动作类型",
            "data": {}  # 额外数据
        }
    }
    """
    try:
        # 解析请求数据
        data = request.json if request.is_json else {}
        message = data.get("message", "")
        user_id = data.get("user_id", f"user_{id(request.remote_addr)}")
        context = data.get("context", {})
        
        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400
        
        # 获取服务实例
        ai_service = get_ai_service()
        
        # 使用异步方式调用 AI 服务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                ai_service.chat(user_id, message, context)
            )
        finally:
            loop.close()
        
        # 记录日志
        logger.info(f"用户 {user_id} 消息：{message[:50]}... -> {result.get('action', 'unknown')}")
        
        # 将 action: tool_call 转换为前端期望的 toolCall 对象格式
        response_data = {"success": True, "message": "处理完成"}
        
        if result.get("action") == "tool_call" and result.get("data"):
            # 构建前端期望的 toolCall 对象
            tool_key = result["data"].get("tool_key")
            if tool_key:
                response_data["toolCall"] = {
                    "tool_id": tool_key,
                    "action": "执行",
                    "params": {
                        "order_text": message,  # 将原始消息作为 order_text 传递
                        **result["data"]  # 包含其他 hint 信息
                    }
                }
                # 同时保留 AI 回复文本
                response_data["response"] = result.get("text", "")
            else:
                # 没有 tool_key，直接返回 AI 回复
                response_data["response"] = result.get("text", "")
                response_data["data"] = result.get("data", {})
        else:
            # 非工具调用场景，直接返回 AI 回复
            response_data["response"] = result.get("text", "")
            response_data["data"] = result.get("data", {})
            # 兼容旧格式：如果有 autoAction，也返回
            if result.get("action") == "auto_action" and result.get("data"):
                response_data["autoAction"] = result["data"]
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"聊天接口异常：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"处理失败：{str(e)}",
        }), 500


@ai_chat_bp.route("/chat-unified", methods=["POST"])
@ai_chat_bp.route("/unified_chat", methods=["POST"])
@swag_from({
    'summary': 'AI 统一聊天接口（兼容旧版）',
    'description': '统一 AI 聊天接口，支持意图识别和工具调用（与 /chat 相同，用于兼容旧版前端）',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': '用户消息'},
                    'user_id': {'type': 'string', 'description': '用户 ID（可选）'},
                    'context': {'type': 'object', 'description': '额外上下文（可选）'}
                },
                'required': ['message']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'}
                }
            }
        }
    }
})
def chat_unified():
    """
    AI 统一聊天接口（兼容旧版前端）
    
    与 /chat 接口功能相同，只是路径不同
    支持路径：/api/ai/chat-unified 和 /api/ai/unified_chat
    """
    return chat()


@ai_chat_bp.route("/chat/stream", methods=["POST"])
@swag_from({
    'summary': 'AI 聊天流式响应',
    'description': 'AI 聊天流式接口，使用 Server-Sent Events 返回实时响应',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': '用户消息'},
                    'user_id': {'type': 'string', 'description': '用户 ID（可选）'}
                },
                'required': ['message']
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'SSE 流式响应'
        }
    }
})
def chat_stream():
    """
    AI 聊天流式接口（Server-Sent Events）
    
    请求格式同 /chat
    响应：SSE 流式输出
    """
    try:
        from flask import Response
        import json
        
        data = request.json if request.is_json else {}
        message = data.get("message", "")
        user_id = data.get("user_id", f"user_{id(request.remote_addr)}")
        
        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400
        
        def generate():
            """生成 SSE 流"""
            ai_service = get_ai_service()
            
            # 使用异步方式调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    ai_service.chat(user_id, message, {})
                )
                
                # 发送完整响应
                yield f"data: {json.dumps(result)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                loop.close()
        
        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        
    except Exception as e:
        logger.error(f"流式聊天接口异常：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"流式处理失败：{str(e)}",
        }), 500


@ai_chat_bp.route("/context", methods=["GET"])
@swag_from({
    'summary': '获取对话上下文',
    'description': '获取当前用户的对话上下文',
    'parameters': [
        {
            'name': 'user_id',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': '用户 ID（可选）'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'context': {'type': 'object'}
                }
            }
        }
    }
})
def get_context():
    """
    获取对话上下文
    
    请求参数：
    - user_id: 用户 ID（可选）
    
    响应：
    {
        "success": True,
        "data": {
            "user_id": "用户 ID",
            "conversation_history": [...],
            "metadata": {...}
        }
    }
    """
    try:
        user_id = request.args.get("user_id", f"user_{id(request.remote_addr)}")
        
        ai_service = get_ai_service()
        context = ai_service.get_context(user_id)
        
        if not context:
            return jsonify({
                "success": True,
                "message": "未找到对话上下文",
                "data": None,
            })
        
        return jsonify({
            "success": True,
            "data": {
                "user_id": context.user_id,
                "conversation_history": context.conversation_history,
                "current_file": context.current_file,
                "last_action": context.last_action,
                "metadata": context.metadata,
            },
        })
        
    except Exception as e:
        logger.error(f"获取上下文失败：{e}")
        return jsonify({
            "success": False,
            "message": f"获取上下文失败：{str(e)}",
        }), 500


@ai_chat_bp.route("/context/clear", methods=["POST"])
@swag_from({
    'summary': '清除对话上下文',
    'description': '清除当前用户的对话上下文',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': False,
            'schema': {
                'type': 'object',
                'properties': {
                    'user_id': {'type': 'string', 'description': '用户 ID（可选）'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def clear_context():
    """
    清除对话上下文
    
    请求参数：
    - user_id: 用户 ID（可选）
    """
    try:
        data = request.json if request.is_json else {}
        user_id = data.get("user_id", f"user_{id(request.remote_addr)}")
        
        ai_service = get_ai_service()
        success = ai_service.clear_context(user_id)
        
        return jsonify({
            "success": success,
            "message": "上下文已清除" if success else "未找到上下文",
        })
        
    except Exception as e:
        logger.error(f"清除上下文失败：{e}")
        return jsonify({
            "success": False,
            "message": f"清除上下文失败：{str(e)}",
        }), 500


@ai_chat_bp.route("/config", methods=["GET"])
@swag_from({
    'summary': '获取 AI 配置',
    'description': '获取 AI 聊天相关配置信息',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'config': {'type': 'object'}
                }
            }
        }
    }
})
def get_config():
    """
    获取 AI 配置信息
    
    响应：
    {
        "success": True,
        "data": {
            "api_configured": True/False,
            "model": "模型名称",
            "features": [...]
        }
    }
    """
    try:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        
        return jsonify({
            "success": True,
            "data": {
                "api_configured": bool(api_key),
                "model": "deepseek-chat",
                "features": [
                    "意图识别",
                    "工具调用",
                    "AI 对话",
                    "上下文管理",
                    "流式输出",
                ],
            },
        })
        
    except Exception as e:
        logger.error(f"获取配置失败：{e}")
        return jsonify({
            "success": False,
            "message": f"获取配置失败：{str(e)}",
        }), 500


@ai_chat_bp.route("/test", methods=["GET"])
@swag_from({
    'summary': '测试 AI 服务',
    'description': '测试 AI 聊天服务是否正常运行',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def test():
    """
    测试接口
    
    响应：
    {
        "success": True,
        "message": "AI 聊天服务运行正常"
    }
    """
    return jsonify({
        "success": True,
        "message": "AI 聊天服务运行正常",
        "timestamp": __import__("time").time(),
    })


# 意图识别测试接口
@ai_chat_bp.route("/intent/test", methods=["POST"])
@swag_from({
    'summary': '测试意图识别',
    'description': '测试消息意图识别功能',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': '测试消息'}
                },
                'required': ['message']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'intents': {'type': 'array'}
                }
            }
        }
    }
})
def test_intent():
    """
    测试意图识别
    
    请求：
    {
        "message": "测试消息"
    }
    
    响应：
    {
        "success": True,
        "data": {
            "primary_intent": "主意图",
            "tool_key": "工具 key",
            "is_greeting": True/False,
            ...
        }
    }
    """
    try:
        data = request.json if request.is_json else {}
        message = data.get("message", "")
        
        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400
        
        # 调用意图识别
        intent_result = recognize_intents(message)
        
        return jsonify({
            "success": True,
            "data": intent_result,
        })
        
    except Exception as e:
        logger.error(f"意图识别测试失败：{e}")
        return jsonify({
            "success": False,
            "message": f"意图识别失败：{str(e)}",
        }), 500
