"""用户认证与会话编排（密码校验、审计日志、委托 SessionService）。"""

import logging
import uuid
from typing import Any

from app.db.models import Permission, Role, User
from app.db.session import get_db
from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin
from app.services.session_service import get_session_service
from app.utils import audit_logger
from app.utils.password_hash import check_password_hash, generate_password_hash
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


class AuthService(NeuroEventPublisherMixin):
    def __init__(self):
        self.session_service = get_session_service()

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.username == username).first()

                if not user:
                    audit_logger.audit_log(
                        "auth_failure",
                        None,
                        "",
                        {"username": username, "reason": "user_not_found"},
                        success=False,
                    )
                    return {"success": False, "message": "用户名或密码错误"}

                if not user.is_active:
                    audit_logger.audit_log(
                        "auth_failure",
                        user.id,
                        "",
                        {"username": username, "reason": "account_disabled"},
                        success=False,
                    )
                    return {"success": False, "message": "账户已被禁用"}

                if not check_password_hash(user.password, password):
                    audit_logger.audit_log(
                        "auth_failure",
                        user.id,
                        "",
                        {"username": username, "reason": "wrong_password"},
                        success=False,
                    )
                    return {"success": False, "message": "用户名或密码错误"}

                user.last_login = utc_now_naive()
                db.commit()

                session_result = self.session_service.create_session(user.id)
                if not session_result["success"]:
                    return {"success": False, "message": "会话创建失败"}

                audit_logger.audit_log(
                    "auth_success", user.id, "", {"username": username, "role": user.role}
                )

                return {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "email": user.email,
                        "role": user.role,
                    },
                    "session_id": session_result["session_id"],
                    "expires_at": session_result["expires_at"],
                }
            except Exception:
                db.rollback()
                err_id = uuid.uuid4().hex[:12]
                logger.exception("authenticate failed (error_id=%s)", err_id)
                return {
                    "success": False,
                    "message": "登录失败，请稍后重试",
                    "error_id": err_id,
                }

    def logout(self, session_id: str) -> bool:
        result = self.session_service.delete_session(session_id)
        audit_logger.audit_log("logout", None, "", {"session_id": session_id, "success": result})
        return result

    def get_current_user(self, session_id: str) -> User | None:
        return self.session_service.validate_session(session_id)

    def get_user_permissions(self, user: User) -> list:
        with get_db() as db:
            if user.role == "admin":
                perms = db.query(Permission).all()
                return [p.code for p in perms]

            role = db.query(Role).filter(Role.name == user.role).first()
            if not role:
                return []
            return [p.code for p in role.permissions]

    def has_permission(self, user: User, permission_code: str) -> bool:
        if user.role == "admin":
            return True

        perms = self.get_user_permissions(user)
        return permission_code in perms

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "message": "用户不存在"}

                if not check_password_hash(user.password, old_password):
                    audit_logger.audit_log(
                        "change_password_failure",
                        user_id,
                        "",
                        {"reason": "wrong_old_password"},
                        success=False,
                    )
                    return {"success": False, "message": "原密码错误"}

                user.password = generate_password_hash(new_password)
                db.commit()
                audit_logger.audit_log("change_password", user_id, "", {"username": user.username})
                return {"success": True, "message": "密码修改成功"}
            except Exception:
                db.rollback()
                err_id = uuid.uuid4().hex[:12]
                logger.exception("change_password failed (error_id=%s user_id=%s)", err_id, user_id)
                return {
                    "success": False,
                    "message": "密码修改失败，请稍后重试",
                    "error_id": err_id,
                }

    def reset_password(self, user_id: int, new_password: str) -> dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "message": "用户不存在"}

                user.password = generate_password_hash(new_password)
                db.commit()
                self.session_service.delete_user_sessions(user_id)
                audit_logger.audit_log("reset_password", user_id, "", {"username": user.username})
                return {"success": True, "message": "密码已重置，请使用新密码登录"}
            except Exception:
                db.rollback()
                err_id = uuid.uuid4().hex[:12]
                logger.exception("reset_password failed (error_id=%s user_id=%s)", err_id, user_id)
                return {
                    "success": False,
                    "message": "密码重置失败，请稍后重试",
                    "error_id": err_id,
                }


def get_auth_service() -> AuthService:
    from app.di.registry import get_service_registry

    return get_service_registry().auth_service


# NEURO-DDD: 为 Services 层类添加 instrumentation
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(AuthService, "app.services.auth_service")
