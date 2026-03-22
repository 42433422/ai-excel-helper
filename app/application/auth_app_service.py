"""
认证应用服务

此模块已迁移到 app/application/
"""

from datetime import datetime
from typing import Any, Dict, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from app.db.models import Permission, Role, User
from app.db.session import get_db
from app.infrastructure.session import get_session_manager


class AuthApplicationService:
    """认证应用服务"""

    def __init__(self):
        self.session_manager = get_session_manager()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """登录方法，调用 authenticate"""
        return self.authenticate(username, password)

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.username == username).first()

                if not user:
                    return {"success": False, "error": "用户名或密码错误"}

                if not user.is_active:
                    return {"success": False, "error": "账户已被禁用"}

                if not check_password_hash(user.password, password):
                    return {"success": False, "error": "用户名或密码错误"}

                user.last_login = datetime.utcnow()
                db.commit()

                session_result = self.session_manager.create_session(user.id)
                if not session_result["success"]:
                    return {"success": False, "error": "会话创建失败"}

                return {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "email": user.email,
                        "role": user.role
                    },
                    "session_id": session_result["session_id"],
                    "expires_at": session_result["expires_at"]
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    def logout(self, session_id: str) -> bool:
        return self.session_manager.delete_session(session_id)

    def get_current_user(self, session_id: str) -> Optional[User]:
        return self.session_manager.validate_session(session_id)

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

    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "error": "用户不存在"}

                if not check_password_hash(user.password, old_password):
                    return {"success": False, "error": "原密码错误"}

                user.password = generate_password_hash(new_password)
                db.commit()
                return {"success": True, "message": "密码修改成功"}
            except Exception as e:
                db.rollback()
                return {"success": False, "error": str(e)}

    def reset_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "error": "用户不存在"}

                user.password = generate_password_hash(new_password)
                db.commit()
                self.session_manager.delete_user_sessions(user_id)
                return {"success": True, "message": "密码已重置，请使用新密码登录"}
            except Exception as e:
                db.rollback()
                return {"success": False, "error": str(e)}


_auth_app_service: Optional[AuthApplicationService] = None


def get_auth_app_service() -> AuthApplicationService:
    global _auth_app_service
    if _auth_app_service is None:
        _auth_app_service = AuthApplicationService()
    return _auth_app_service
