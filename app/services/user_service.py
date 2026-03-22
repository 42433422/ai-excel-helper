from datetime import datetime
from typing import Any, Dict, List, Optional

from werkzeug.security import generate_password_hash

from app.db.models import User
from app.db.session import get_db


class UserService:
    def __init__(self):
        pass

    def list_users(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        with get_db() as db:
            query = db.query(User)
            if not include_inactive:
                query = query.filter(User.is_active == True)
            users = query.order_by(User.created_at.desc()).all()
            return [self._user_to_dict(u) for u in users]

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            return self._user_to_dict(user)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
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
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            try:
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    return {"success": False, "error": "用户名已存在"}

                user = User(
                    username=username,
                    password=generate_password_hash(password),
                    display_name=display_name or username,
                    email=email,
                    role=role,
                    is_active=True,
                    created_by=created_by,
                    created_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return {"success": True, "user": self._user_to_dict(user)}
            except Exception as e:
                db.rollback()
                return {"success": False, "error": str(e)}

    def update_user(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "error": "用户不存在"}

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
            except Exception as e:
                db.rollback()
                return {"success": False, "error": str(e)}

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        with get_db() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "error": "用户不存在"}

                user.is_active = False
                db.commit()
                return {"success": True, "message": "用户已删除"}
            except Exception as e:
                db.rollback()
                return {"success": False, "error": str(e)}

    def _user_to_dict(self, user: User) -> Dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_by": user.created_by,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }


_user_service = None


def get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
