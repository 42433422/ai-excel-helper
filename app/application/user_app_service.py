"""
用户应用服务

此模块已迁移到 app/application/
"""

from typing import Any

from app.db.models import User
from app.db.session import get_db
from app.utils.password_hash import generate_password_hash


class UserApplicationService:
    """用户应用服务"""

    def __init__(self):
        pass

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            return {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return None
            return {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            }

    def list_users(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with get_db() as db:
            users = db.query(User).offset(skip).limit(limit).all()
            return [
                {
                    "id": u.id,
                    "username": u.username,
                    "display_name": u.display_name,
                    "email": u.email,
                    "role": u.role,
                    "is_active": u.is_active,
                }
                for u in users
            ]

    def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        email: str = "",
        role: str = "user",
    ) -> dict[str, Any]:
        with get_db() as db:
            try:
                user = User(
                    username=username,
                    password=generate_password_hash(password),
                    display_name=display_name or username,
                    email=email,
                    role=role,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "email": user.email,
                        "role": user.role,
                    },
                }
            except Exception as e:
                db.rollback()
                return {"success": False, "message": str(e)}

    def update_user(
        self,
        user_id: int,
        display_name: str | None = None,
        email: str | None = None,
        role: str | None = None,
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

                db.commit()
                return {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "email": user.email,
                        "role": user.role,
                    },
                }
            except Exception as e:
                db.rollback()
                return {"success": False, "message": str(e)}

    def delete_user(self, user_id: int) -> dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "message": "用户不存在"}

                user.is_active = False
                db.commit()
                return {"success": True, "message": "用户已禁用"}
            except Exception as e:
                db.rollback()
                return {"success": False, "message": str(e)}


from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(UserApplicationService)

_user_app_service: UserApplicationService | None = None


def get_user_app_service() -> UserApplicationService:
    global _user_app_service
    if _user_app_service is None:
        _user_app_service = UserApplicationService()
    return _user_app_service
