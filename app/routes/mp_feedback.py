# -*- coding: utf-8 -*-
"""
小程序用户反馈 API
"""
import json
import logging

from flask import Blueprint, request

from app.db.models import MpFeedback
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, paginate, success

logger = logging.getLogger(__name__)

mp_feedback_bp = Blueprint("mp_feedback", __name__, url_prefix="/api/mp/v1/feedback")


@mp_feedback_bp.route("/submit", methods=["POST"])
@mp_auth_required
def feedback_submit():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}

    fb_type = data.get("type", "").strip()
    content = data.get("content", "").strip()
    images = data.get("images", [])

    valid_types = ["bug", "suggestion", "complaint", "other"]
    if fb_type not in valid_types:
        return error("反馈类型无效", 400)
    if not content:
        return error("反馈内容不能为空", 400)
    if len(content) > 1000:
        return error("反馈内容不能超过1000字", 400)

    with get_db() as db:
        feedback = MpFeedback(
            user_id=user_id,
            type=fb_type,
            content=content,
            images=json.dumps(images) if images else None,
            status="pending",
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return success({"feedback_id": feedback.id}, "提交成功，感谢您的反馈！")


@mp_feedback_bp.route("/list", methods=["GET"])
@mp_auth_required
def feedback_list():
    user_id = get_current_mp_user_id()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(50, max(1, request.args.get("page_size", 20, type=int)))

    with get_db() as db:
        query = (
            db.query(MpFeedback)
            .filter(MpFeedback.user_id == user_id)
            .order_by(MpFeedback.created_at.desc())
        )
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for fb in items:
            result.append({
                "id": fb.id,
                "type": fb.type,
                "content": fb.content[:200],
                "status": fb.status,
                "has_reply": bool(fb.reply),
                "replied_at": fb.replied_at.isoformat() if fb.replied_at else None,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            })

        return paginate(result, total, page, page_size)


@mp_feedback_bp.route("/detail/<int:feedback_id>", methods=["GET"])
@mp_auth_required
def feedback_detail(feedback_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        fb = db.query(MpFeedback).filter(
            MpFeedback.id == feedback_id,
            MpFeedback.user_id == user_id,
        ).first()

        if not fb:
            return error("反馈不存在", 404)

        images = []
        if fb.images:
            try:
                images = json.loads(fb.images)
            except Exception:
                pass

        return success({
            "id": fb.id,
            "type": fb.type,
            "content": fb.content,
            "images": images,
            "status": fb.status,
            "reply": fb.reply or "",
            "replied_at": fb.replied_at.isoformat() if fb.replied_at else None,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        })
