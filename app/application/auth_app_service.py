"""认证应用服务：登录/改密/重置密码，委托 SessionManager 与会话基础设施。"""

import logging
import uuid
from typing import Any

from app.db.models import Permission, Role, User
from app.db.session import get_db
from app.infrastructure.session import get_session_manager
from app.utils.password_hash import check_password_hash, generate_password_hash
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


def _authenticate_failure_message(exc: BaseException) -> str:
    """将典型数据库/结构错误映射为可操作的登录提示（避免一律显示「稍后重试」）。"""
    chunks: list[str] = []
    cur: BaseException | None = exc
    seen: set[int] = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        chunks.append(str(cur).lower())
        orig = getattr(cur, "orig", None)
        if orig is not None:
            chunks.append(str(orig).lower())
        cur = cur.__cause__ or getattr(cur, "__context__", None)
    blob = " ".join(chunks)
    if "market_access_token" in blob:
        return (
            "数据库表 sessions 缺少 market_access_token 列，无法保存登录会话。"
            "请在服务器 FHD 目录执行 alembic upgrade head，或重启后端由启动逻辑自动补齐该列。"
        )
    if "no such table: users" in blob:
        return (
            "本地 SQLite 缺少 users 表。请重启后端（将自动创建），"
            '或在 FHD 目录执行：python -c "from app.db.init_db import ensure_runtime_auth_bootstrap; ensure_runtime_auth_bootstrap()"'
        )
    if 'relation "users"' in blob or ("users" in blob and "does not exist" in blob):
        return (
            "数据库缺少 users 表（尚未执行迁移或空库未自动引导）。"
            "请在服务器 FHD 目录执行 alembic upgrade head，或重启后端以触发 PostgreSQL 登录表自动补齐。"
        )
    if 'relation "sessions"' in blob or ("sessions" in blob and "does not exist" in blob):
        return (
            "数据库缺少 sessions 表，无法创建登录会话。"
            "请在服务器 FHD 目录执行 alembic upgrade head，或重启后端以触发 PostgreSQL 登录表自动补齐。"
        )
    return "登录失败，请稍后重试"


class AuthApplicationService:
    """认证应用服务"""

    def __init__(self):
        self.session_manager = get_session_manager()

    def login(self, username: str, password: str) -> dict[str, Any]:
        """登录方法，调用 authenticate"""
        return self.authenticate(username, password)

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        try:
            from app.db.init_db import ensure_runtime_auth_bootstrap

            ensure_runtime_auth_bootstrap(swallow_errors=True)
        except Exception as bootstrap_exc:
            logger.warning("登录前 auth 表自检跳过: %s", bootstrap_exc)
        try:
            with get_db() as db:
                user = db.query(User).filter(User.username == username).first()

                if not user:
                    return {"success": False, "message": "用户名或密码错误"}

                if not user.is_active:
                    return {"success": False, "message": "账户已被禁用"}

                if not check_password_hash(user.password, password):
                    return {"success": False, "message": "用户名或密码错误"}

                user.last_login = utc_now_naive()
                session_result = self.session_manager.create_session_with_db(db, user.id)
                if not session_result["success"]:
                    return {"success": False, "message": "会话创建失败"}

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
        except Exception as exc:
            err_id = uuid.uuid4().hex[:12]
            logger.exception("authenticate failed (error_id=%s)", err_id)
            return {
                "success": False,
                "message": _authenticate_failure_message(exc),
                "error_id": err_id,
            }

    def logout(self, session_id: str) -> bool:
        return self.session_manager.delete_session(session_id)

    def get_current_user(self, session_id: str) -> User | None:
        return self.session_manager.validate_session(session_id)

    def get_user_permissions(self, user: User) -> list:
        try:
            from app.db.init_db import ensure_runtime_auth_bootstrap

            ensure_runtime_auth_bootstrap(swallow_errors=True)
        except Exception as bootstrap_exc:
            logger.warning("权限表自检跳过: %s", bootstrap_exc)
        try:
            with get_db() as db:
                if user.role == "admin":
                    perms = db.query(Permission).all()
                    return [p.code for p in perms]

                role = db.query(Role).filter(Role.name == user.role).first()
                if not role:
                    return []
                return [p.code for p in role.permissions]
        except Exception as exc:
            logger.warning("get_user_permissions 回退为空列表: %s", exc)
            if user.role == "admin":
                from app.db.models.permission import DEFAULT_PERMISSIONS

                return [p["code"] for p in DEFAULT_PERMISSIONS]
            return []

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
                    return {"success": False, "message": "原密码错误"}

                user.password = generate_password_hash(new_password)
                db.commit()
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
                self.session_manager.delete_user_sessions(user_id)
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


from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(AuthApplicationService)

_auth_app_service: AuthApplicationService | None = None


def get_auth_app_service() -> AuthApplicationService:
    global _auth_app_service
    if _auth_app_service is None:
        _auth_app_service = AuthApplicationService()
    return _auth_app_service
