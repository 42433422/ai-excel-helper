from __future__ import annotations

from fastapi.testclient import TestClient

from app.desktop_runtime import configure_desktop_environment
from app.fastapi_app import create_fastapi_app


def test_desktop_status_api_local_sqlite(tmp_path, monkeypatch):
    from app.security.lan_config import get_lan_config, reset_lan_config_cache
    from app.security.lan_settings_store import LanSettingsOverride

    monkeypatch.setenv("XCAGI_DESKTOP_MODE", "1")
    monkeypatch.setenv("LAN_GUARD_ENABLED", "0")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("XCAGI_DESKTOP_KEEP_DATABASE_URL", raising=False)
    monkeypatch.setattr(
        "app.security.lan_settings_store.load_overrides",
        lambda: LanSettingsOverride(enabled=False),
    )
    reset_lan_config_cache()

    configure_desktop_environment(tmp_path)

    client = TestClient(create_fastapi_app())
    response = client.get("/api/desktop/status")
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["desktopMode"] is True
    assert payload["storageMode"] == "local_sqlite"
    assert "xcagi.db" in payload["database"]
    assert payload["databaseUrlRedacted"]
    assert payload["profilePath"]
    assert str(tmp_path) in payload["dataDir"] or str(tmp_path.resolve()) in payload["dataDir"]
    assert "modsFullLoadDone" in payload
    assert "modsBackgroundLoadScheduled" in payload
    assert "startupTiming" in payload
    assert payload.get("readyForUi") is True
