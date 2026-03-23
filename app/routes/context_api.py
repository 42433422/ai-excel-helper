# -*- coding: utf-8 -*-
"""
上下文状态 API 和 WebSocket 模块

提供：
- GET /api/context/pending/{user_id} - 获取 pending 状态
- WebSocket /ws/context - 实时推送 pending 状态变化
"""

import asyncio
import json
import logging
import threading
from typing import Any, Dict, Set

from flask import Blueprint, jsonify, request
from flask_socketio import emit, join_room, leave_room

logger = logging.getLogger(__name__)

context_api_bp = Blueprint("context_api", __name__, url_prefix="/api/context")

_websocket_clients: Dict[str, Set[str]] = {}

_notification_queue: asyncio.Queue = None
_notification_thread: threading.Thread = None


class ContextNotifier:
    """
    上下文状态变化通知器

    单例模式，管理 WebSocket 连接和状态推送
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._clients: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def register_client(self, user_id: str, sid: str) -> None:
        """注册客户端连接"""
        with self._lock:
            if user_id not in self._clients:
                self._clients[user_id] = set()
            self._clients[user_id].add(sid)
            logger.info(f"[CONTEXT_NOTIFIER] Client registered: user={user_id}, sid={sid}")

    def unregister_client(self, user_id: str, sid: str) -> None:
        """取消注册客户端"""
        with self._lock:
            if user_id in self._clients:
                self._clients[user_id].discard(sid)
                if not self._clients[user_id]:
                    del self._clients[user_id]
                logger.info(f"[CONTEXT_NOTIFIER] Client unregistered: user={user_id}, sid={sid}")

    def notify_pending_created(self, user_id: str, pending_data: Dict[str, Any]) -> None:
        """通知 pending 创建"""
        self._emit(user_id, {
            "type": "pending_created",
            "pending": pending_data
        })

    def notify_pending_updated(self, user_id: str, pending_data: Dict[str, Any]) -> None:
        """通知 pending 更新"""
        self._emit(user_id, {
            "type": "pending_updated",
            "pending": pending_data
        })

    def notify_pending_cleared(self, user_id: str, reason: str = "completed") -> None:
        """通知 pending 清除"""
        self._emit(user_id, {
            "type": "pending_cleared",
            "reason": reason
        })

    def notify_pending_preserved(self, user_id: str, pending_data: Dict[str, Any], action: str) -> None:
        """通知 pending 保留（特殊意图时）"""
        self._emit(user_id, {
            "type": "pending_preserved",
            "pending": pending_data,
            "action": action,
            "message": "当前任务已暂停，可随时继续"
        })

    def _emit(self, user_id: str, data: Dict[str, Any]) -> None:
        """发送消息给客户端"""
        if user_id not in self._clients:
            return

        message = json.dumps(data, ensure_ascii=False)
        sids = list(self._clients[user_id])

        for sid in sids:
            try:
                from flask_socketio import emit as socket_emit
                socket_emit("context_update", data, room=sid)
                logger.debug(f"[CONTEXT_NOTIFIER] Emitted to {sid}: {data['type']}")
            except Exception as e:
                logger.error(f"[CONTEXT_NOTIFIER] Failed to emit to {sid}: {e}")
                self.unregister_client(user_id, sid)


_context_notifier: ContextNotifier = None


def get_context_notifier() -> ContextNotifier:
    """获取 ContextNotifier 单例"""
    global _context_notifier
    if _context_notifier is None:
        _context_notifier = ContextNotifier()
    return _context_notifier


@context_api_bp.route("/pending/<user_id>", methods=["GET"])
def get_pending_status(user_id: str):
    """
    获取用户的 pending 状态

    GET /api/context/pending/{user_id}

    Returns:
        {
            "success": true,
            "pending": {
                "intent": "shipment_generate",
                "slots": {...},
                "missing_slots": [...],
                "turn_count": 2,
                "created_at": 1234567890.123,
                "is_expired": false
            }
        }
    """
    try:
        from app.domain.services.conversation.context import get_context_facade

        facade = get_context_facade()
        summary = facade.get_context_summary(user_id)

        return jsonify({
            "success": True,
            "pending": summary.get("pending", {})
        })
    except Exception as e:
        logger.error(f"[CONTEXT_API] Failed to get pending: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@context_api_bp.route("/pending/<user_id>", methods=["DELETE"])
def clear_pending(user_id: str):
    """
    清除用户的 pending 状态

    DELETE /api/context/pending/{user_id}

    Returns:
        {"success": true}
    """
    try:
        from app.domain.services.conversation.context import get_context_facade

        facade = get_context_facade()
        facade.cancel_pending(user_id)

        notifier = get_context_notifier()
        notifier.notify_pending_cleared(user_id, "manual_cleared")

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"[CONTEXT_API] Failed to clear pending: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@context_api_bp.route("/history/<user_id>", methods=["GET"])
def get_chat_history(user_id: str):
    """
    获取用户的聊天历史摘要

    GET /api/context/history/{user_id}

    Returns:
        {
            "success": true,
            "history": {
                "has_history": true,
                "count": 10,
                "recent_intents": ["shipment_generate", "products"],
                "last_message": "生成发货单",
                "last_intent": "shipment_generate"
            }
        }
    """
    try:
        from app.domain.services.conversation.context import get_context_facade

        facade = get_context_facade()
        summary = facade.get_context_summary(user_id)

        return jsonify({
            "success": True,
            "history": summary.get("history", {})
        })
    except Exception as e:
        logger.error(f"[CONTEXT_API] Failed to get history: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def register_socketio_handlers(socketio):
    """
    注册 SocketIO 事件处理器

    在 Flask-SocketIO 初始化后调用此函数

    Args:
        socketio: Flask-SocketIO 实例
    """

    @socketio.on("connect", namespace="/ws/context")
    def handle_connect():
        """处理客户端连接"""
        logger.info(f"[SOCKET] Client connected: {request.sid}")

    @socketio.on("disconnect", namespace="/ws/context")
    def handle_disconnect():
        """处理客户端断开"""
        logger.info(f"[SOCKET] Client disconnected: {request.sid}")

    @socketio.on("subscribe", namespace="/ws/context")
    def handle_subscribe(data):
        """
        客户端订阅用户上下文

        Client sends: {"user_id": "user123"}
        """
        user_id = data.get("user_id", "default")
        join_room(request.sid)

        notifier = get_context_notifier()
        notifier.register_client(user_id, request.sid)

        from app.domain.services.conversation.context import get_context_facade
        facade = get_context_facade()
        summary = facade.get_context_summary(user_id)

        emit("subscribed", {
            "success": True,
            "user_id": user_id,
            "pending": summary.get("pending", {})
        })
        logger.info(f"[SOCKET] User {user_id} subscribed with sid {request.sid}")

    @socketio.on("unsubscribe", namespace="/ws/context")
    def handle_unsubscribe(data):
        """
        客户端取消订阅
        """
        user_id = data.get("user_id", "default")
        leave_room(request.sid)

        notifier = get_context_notifier()
        notifier.unregister_client(user_id, request.sid)

        emit("unsubscribed", {"success": True, "user_id": user_id})
        logger.info(f"[SOCKET] User {user_id} unsubscribed")

    @socketio.on("ping", namespace="/ws/context")
    def handle_ping(data):
        """心跳检测"""
        emit("pong", {"timestamp": __import__("time").time()})
