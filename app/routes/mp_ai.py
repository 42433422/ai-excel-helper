# -*- coding: utf-8 -*-
"""
小程序 AI 智能客服 API
"""
import logging

from flask import Blueprint, request

from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, success

logger = logging.getLogger(__name__)

mp_ai_bp = Blueprint("mp_ai", __name__, url_prefix="/api/mp/v1/ai")


@mp_ai_bp.route("/chat", methods=["POST"])
@mp_auth_required
def ai_chat():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id")

    if not message:
        return error("消息内容不能为空", 400)

    try:
        from app.services.ai_conversation_service import AIConversationService
        service = AIConversationService()

        response_text = service.chat(
            message=message,
            user_id=user_id,
            session_id=session_id,
            source="miniprogram",
        )

        return success({
            "reply": response_text,
            "message": message,
        })

    except Exception as e:
        logger.error(f"AI 对话异常: {e}", exc_info=True)
        return error(f"AI 服务暂时不可用: {str(e)}", 500)


@mp_ai_bp.route("/history", methods=["GET"])
@mp_auth_required
def ai_history():
    user_id = get_current_mp_user_id()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(50, max(1, request.args.get("page_size", 20, type=int)))

    try:
        from app.db.models import AIConversationSession, AIConversation
        from app.db.session import get_db

        with get_db() as db:
            sessions = (
                db.query(AIConversationSession)
                .filter(AIConversationSession.user_id == user_id)
                .order_by(AIConversationSession.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            result = []
            for session in sessions:
                last_msg = (
                    db.query(AIConversation)
                    .filter(AIConversation.session_id == session.id)
                    .order_by(AIConversation.created_at.desc())
                    .first()
                )
                result.append({
                    "session_id": session.id,
                    "last_message": last_msg.content[:100] if last_msg else "",
                    "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                })

            return success(result)

    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        return error("获取历史失败", 500)


@mp_ai_bp.route("/intents", methods=["GET"])
def ai_intents():
    intents = [
        {"key": "price_inquiry", "label": "询价", "example": "这个产品多少钱？"},
        {"key": "product_search", "label": "找产品", "example": "有没有白色的底漆？"},
        {"key": "order_status", "label": "查订单", "example": "我的订单到哪了？"},
        {"key": "after_sales", "label": "售后", "example": "产品质量有问题怎么办？"},
        {"key": "other", "label": "其他问题", "example": "我想咨询其他问题"},
    ]
    return success(intents)
