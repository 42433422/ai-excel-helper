"""AuthService / UserService / SessionService 关键路径（Mock DB）。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.auth_service import AuthService
from app.services.session_service import SessionService
from app.services.user_service import UserService


def _db_cm(mock_db):
    cm = MagicMock()
    cm.__enter__.return_value = mock_db
    cm.__exit__.return_value = None
    return cm


def _user_row():
    u = MagicMock()
    u.id = 42
    u.username = "tuser"
    u.display_name = "T User"
    u.email = "t@example.com"
    u.role = "viewer"
    u.is_active = True
    u.password = "hashed-secret"
    return u


@patch("app.services.auth_service.audit_logger")
@patch("app.services.auth_service.check_password_hash", return_value=True)
@patch("app.services.auth_service.get_db")
def test_auth_service_authenticate_success(mock_get_db, _chk, _audit):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = _user_row()
    mock_get_db.return_value = _db_cm(mock_db)

    mock_sessions = MagicMock()
    mock_sessions.create_session.return_value = {
        "success": True,
        "session_id": "sess-uuid",
        "expires_at": "2099-01-01T00:00:00",
    }

    svc = AuthService()
    svc.session_service = mock_sessions

    out = svc.authenticate("tuser", "secret")
    assert out["success"] is True
    assert out["session_id"] == "sess-uuid"
    assert out["user"]["username"] == "tuser"
    mock_db.commit.assert_called()
    mock_sessions.create_session.assert_called_once_with(42)


@patch("app.services.auth_service.audit_logger")
@patch("app.services.auth_service.get_db")
def test_auth_service_authenticate_unknown_user(mock_get_db, _audit):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_get_db.return_value = _db_cm(mock_db)

    svc = AuthService()
    svc.session_service = MagicMock()
    out = svc.authenticate("nope", "x")
    assert out["success"] is False
    assert "用户名" in out["message"]


@patch("app.services.user_service.get_db")
def test_user_service_create_user_duplicate(mock_get_db):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    mock_get_db.return_value = _db_cm(mock_db)

    out = UserService().create_user("dup", "pw")
    assert out["success"] is False
    assert "已存在" in out["message"]


@patch("app.infrastructure.session.session_manager.get_db")
def test_session_service_validate_expired_deletes(mock_get_db):
    sess_row = MagicMock()
    sess_row.expires_at = datetime(2000, 1, 1)
    sess_row.user = MagicMock()

    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
        sess_row
    )
    mock_get_db.return_value = _db_cm(mock_db)

    SessionService().validate_session("any-id")

    mock_db.delete.assert_called_once_with(sess_row)
    mock_db.commit.assert_called()
