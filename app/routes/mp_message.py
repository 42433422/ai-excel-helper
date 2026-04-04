# -*- coding: utf-8 -*-
"""
小程序消息通知 API
"""
import logging

from flask import Blueprint, request

from app.db.models import MpNotification
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, paginate, success

logger = logging.getLogger(__name__)

mp_message_bp = Blueprint("mp_message", __name__, url_prefix="/api/mp/v1/message")


@mp_message_bp.route("/list", methods=["GET"])
@mp_auth_required
def message_list():
    user_id = get_current_mp_user_id()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(50, max(1, request.args.get("page_size", 20, type=int)))
    msg_type = request.args.get("type", "").strip()

    with get_db() as db:
        query = db.query(MpNotification).filter(MpNotification.user_id == user_id)

        if msg_type and msg_type != "all":
            query = query.filter(MpNotification.type == msg_type)

        query = query.order_by(MpNotification.created_at.desc())
        total = query.count()
        messages = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for msg in messages:
            result.append({
                "id": msg.id,
                "title": msg.title,
                "content": (msg.content or "")[:200],
                "type": msg.type,
                "is_read": msg.is_read,
                "related_type": msg.related_type,
                "related_id": msg.related_id,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })

        return paginate(result, total, page, page_size)


@mp_message_bp.route("/read/<int:msg_id>", methods=["PUT"])
@mp_auth_required
def message_read(msg_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        msg = db.query(MpNotification).filter(
            MpNotification.id == msg_id,
            MpNotification.user_id == user_id,
        ).first()

        if not msg:
            return error("消息不存在", 404)

        msg.is_read = True
        db.commit()

        return success(message="已标记为已读")


@mp_message_bp.route("/read-all", methods=["PUT"])
@mp_auth_required
def message_read_all():
    user_id = get_current_mp_user_id()
    with get_db() as db:
        db.query(MpNotification).filter(
            MpNotification.user_id == user_id,
            MpNotification.is_read == False,
        ).update({"is_read": True})

        db.commit()
        return success(message="全部已读")


@mp_message_bp.route("/unread-count", methods=["GET"])
@mp_auth_required
def unread_count():
    user_id = get_current_mp_user_id()
    with get_db() as db:
        count = db.query(MpNotification).filter(
            MpNotification.user_id == user_id,
            MpNotification.is_read == False,
        ).count()

        return success({"count": count})
