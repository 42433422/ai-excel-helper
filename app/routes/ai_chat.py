# -*- coding: utf-8 -*-
"""
AI 聊天路由模块

提供 AI 聊天接口，包括：
- /api/ai/chat: 统一聊天接口
- /api/ai/chat-unified: 兼容旧版
- /api/ai/chat/stream: 流式响应
- /api/ai/file/analyze: 文件分析
- /api/ai/sqlite/import_unit_products: 产品导入
"""

import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from app.utils.path_utils import get_upload_dir
from app.utils.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

ai_chat_bp = Blueprint("ai_chat", __name__, url_prefix="/api/ai")

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
    "excel_analyzer": {
        "keywords": ["分析 excel", "分析模板", "模板分析", "excel 结构", "模板结构", "可编辑区域"],
        "priority": 8,
    },
    "excel_toolkit": {
        "keywords": ["查看 excel", "查看内容", "Excel 内容", "合并单元格", "样式信息"],
        "priority": 7,
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
        "keywords": ["打印", "标签", "打印标签", "商标导出", "标签导出", "商标打印", "商标"],
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
    from app.services import get_ai_conversation_service
    return get_ai_conversation_service()


def set_file_pending_confirmation(user_id: str, pending_data: Dict[str, Any]) -> None:
    """设置文件上传待确认上下文"""
    ai_service = get_ai_service()
    ai_service.set_pending_confirmation(user_id, pending_data)


def recognize_intents(message: str) -> Dict[str, Any]:
    """导入意图识别函数"""
    from app.services import recognize_intents
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
        data = request.json if request.is_json else {}
        message = data.get("message", "")
        user_id = data.get("user_id", f"user_{request.remote_addr}")
        context = data.get("context", {})
        source = (data.get("source") or "").strip().lower()
        file_context = data.get("file_context", {})

        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400

        rate_limit_result = check_rate_limit(
            user_id=user_id,
            endpoint="ai_chat",
            max_requests=10,
            window_seconds=60
        )
        if not rate_limit_result.get("allowed"):
            return jsonify({
                "success": False,
                "message": "请求过于频繁，请稍后再试",
                "retry_after": rate_limit_result.get("retry_after", 60)
            }), 429

        from app.application import AIChatApplicationService, get_ai_chat_app_service
        ai_chat_service = get_ai_chat_app_service()

        result = ai_chat_service.process_chat(
            user_id=user_id,
            message=message,
            context=context,
            source=source,
            file_context=file_context
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"聊天接口异常：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"处理失败：{str(e)}",
        }), 500


@ai_chat_bp.route("/chat-unified", methods=["POST"])
@ai_chat_bp.route("/unified_chat", methods=["POST"])
def chat_unified():
    """AI 统一聊天接口（兼容旧版前端）"""
    return chat()


@ai_chat_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """AI 聊天流式接口（Server-Sent Events）"""
    try:
        import json

        from flask import Response

        data = request.json if request.is_json else {}
        message = data.get("message", "")
        user_id = data.get("user_id", f"user_{request.remote_addr}")

        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400

        def generate():
            ai_service = get_ai_service()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    ai_service.chat(user_id, message, {})
                )
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
def get_context():
    """获取对话上下文"""
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
def clear_context():
    """清除对话上下文"""
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
def get_config():
    """获取 AI 配置"""
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
def test():
    """测试 AI 服务"""
    return jsonify({
        "success": True,
        "message": "AI 聊天服务运行正常",
        "timestamp": __import__("time").time(),
    })


@ai_chat_bp.route("/intent/test", methods=["POST"])
def test_intent():
    """测试意图识别"""
    try:
        data = request.json if request.is_json else {}
        message = data.get("message", "")

        if not message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空",
            }), 400

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


@ai_chat_bp.route("/file/analyze", methods=["POST"])
def file_analyze():
    """
    统一文件分析接口
    支持 .db（SQLite）读取，返回库内表结构摘要
    """
    try:
        upload_file = request.files.get("file")
        purpose = request.form.get("purpose", "general")

        from app.application import FileAnalysisService, get_file_analysis_app_service
        service = get_file_analysis_app_service()

        result = service.analyze_file(upload_file, purpose)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.exception(f"文件分析失败：{e}")
        return jsonify({
            "success": False,
            "message": f"文件分析失败：{str(e)}"
        }), 500


@ai_chat_bp.route("/sqlite/import_unit_products", methods=["POST"])
def import_unit_products():
    """
    从上传的 SQLite .db 导入购买单位产品
    """
    try:
        payload = request.get_json() or {}
        saved_name = payload.get("saved_name") or ""
        unit_name = (payload.get("unit_name") or payload.get("unit_name_guess") or "").strip()
        create_purchase_unit = bool(payload.get("create_purchase_unit", True))
        skip_duplicates = bool(payload.get("skip_duplicates", True))

        from app.application import UnitProductsImportService, get_unit_products_import_app_service
        service = get_unit_products_import_app_service()

        result = service.import_unit_products(
            saved_name=saved_name,
            unit_name=unit_name,
            create_purchase_unit=create_purchase_unit,
            skip_duplicates=skip_duplicates
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.exception(f"导入购买单位+产品列表失败：{e}")
        return jsonify({
            "success": False,
            "message": f"导入失败：{str(e)}"
        }), 500