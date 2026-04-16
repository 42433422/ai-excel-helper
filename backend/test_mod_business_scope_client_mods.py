"""mod_business_scope：原版模式请求上下文（不依赖 PostgreSQL / backend/tests/conftest）。"""

from __future__ import annotations

from backend.request_client_mods_ctx import (
    reset_request_client_mods_ui_off,
    set_request_client_mods_ui_off,
)
from backend.shell import mod_business_scope as m


def test_business_data_exposed_false_when_client_mods_header_ctx_on(monkeypatch):
    monkeypatch.delenv("FHD_BUSINESS_DATA_REQUIRES_EXTENSION_MOD", raising=False)
    tok = set_request_client_mods_ui_off(True)
    try:
        assert m.business_data_exposed() is False
        reason = m.business_data_hidden_reason()
        assert reason and "原版模式" in reason
    finally:
        reset_request_client_mods_ui_off(tok)


def test_business_data_exposed_true_when_ctx_off_even_without_extension(monkeypatch):
    monkeypatch.setenv("FHD_BUSINESS_DATA_REQUIRES_EXTENSION_MOD", "1")
    monkeypatch.setattr("backend.shell.mod_business_scope.extension_mod_manifest_rows", lambda: [])
    tok = set_request_client_mods_ui_off(False)
    try:
        assert m.business_data_exposed() is False
    finally:
        reset_request_client_mods_ui_off(tok)
