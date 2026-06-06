"""用户 CRUD 服务：列表/查询/创建/更新/软删，不负责认证与权限策略。"""

import logging
import uuid
from typing import Any

from app.db.models import User
from app.db.session import get_db
from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin
from app.utils.password_hash import generate_password_hash
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


class UserService(NeuroEventPublisherMixin):
    def __init__(self):
        pass

    def list_users(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        with get_db() as db:
            query = db.query(User)
            if not include_inactive:
                query = query.filter(User.is_active.is_(True))
            users = query.order_by(User.created_at.desc()).all()
            return [self._user_to_dict(u) for u in users]

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            return self._user_to_dict(user)

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return None
            return self._user_to_dict(user)

    def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        email: str = "",
        role: str = "viewer",
        created_by: int | None = None,
    ) -> dict[str, Any]:
        with get_db() as db:
            try:
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    return {"success": False, "message": "用户名已存在"}

                user = User(
                    username=username,
                    password=generate_password_hash(password),
                    display_name=display_name or username,
                    email=email,
                    role=role,
                    is_active=True,
                    created_by=created_by,
                    created_at=utc_now_naive(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return {"success": True, "user": self._user_to_dict(user)}
            except Exception:
                db.rollback()
                err_id = uuid.uuid4().hex[:12]
                logger.exception("create_user failed (error_id=%s username=%s)", err_id, username)
                return {
                    "success": False,
                    "message": "创建用户失败，请稍后重试",
                    "error_id": err_id,
                }

    def update_user(
        self,
        user_id: int,
        display_name: str | None = None,
        email: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "message": "用户不存在"}

                if display_name is not None:
                    user.display_name = display_name
                if email is not None:
                    user.email = email
                if role is not None:
                    user.role = role
                if is_active is not None:
                    user.is_active = is_active

                db.commit()
                db.refresh(user)
                return {"success": True, "user": self._user_to_dict(user)}
            except Exception:
                db.rollback()
                err_id = uuid.uuid4().hex[:12]
                logger.exception("update_user failed (error_id=%s user_id=%s)", err_id, user_id)
                return {
                    "success": False,
                    "message": "更新用户失败，请稍后重试",
                    "error_id": err_id,
                }

    def delete_user(self, user_id: int) -> dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "message": "用户不存在"}

                user.is_active = False
                db.commit()
                return {"success": True, "message": "用户已删除"}
            except Exception:
                db.rollback()
                err_id = uuid.uuid4().hex[:12]
                logger.exception("delete_user failed (error_id=%s user_id=%s)", err_id, user_id)
                return {
                    "success": False,
                    "message": "删除用户失败，请稍后重试",
                    "error_id": err_id,
                }

    def _user_to_dict(self, user: User) -> dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_by": user.created_by,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }


def get_user_service() -> UserService:
    from app.di.registry import get_service_registry

    return get_service_registry().user_service


# NEURO-DDD: 为 Services 层类添加 instrumentation
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(UserService, "app.services.user_service")
