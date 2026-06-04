from __future__ import annotations

import json
import os

from app.desktop_runtime.database_profile import (
    apply_database_profile_to_env,
    load_or_create_profile,
    resolve_storage_mode,
)
from app.desktop_runtime.model_downloader import load_manifest
from app.desktop_runtime.paths import (
    configure_desktop_environment,
    ensure_desktop_dirs,
    sqlite_database_url,
)


def test_configure_desktop_environment_sets_local_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)

    data_dir = configure_desktop_environment(tmp_path)

    assert data_dir == tmp_path.resolve()
    assert os.environ["XCAGI_DESKTOP_MODE"] == "1"
    assert os.environ["DATABASE_URL"].startswith("sqlite:///")
    assert os.environ["XCAGI_MOD_ISOLATED_DATABASES"] == "0"
    assert os.environ["CACHE_REDIS_URL"] == ""
    assert os.environ["CELERY_BROKER_URL"] == "memory://"
    prof_path, profile = load_or_create_profile(tmp_path)
    assert prof_path.is_file()
    assert profile["mode"] == "local"
    assert profile["remote"]["enabled"] is False


def test_database_profile_creates_default_json(tmp_path):
    path, profile = load_or_create_profile(tmp_path)
    assert path.name == "database.json"
    assert path.parent.name == "config"
    assert profile["mode"] == "local"


def test_resolve_storage_mode_local_sqlite():
    assert resolve_storage_mode("sqlite:///C:/data/xcagi.db") == "local_sqlite"


def test_apply_database_profile_remote_when_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    prof_path, _ = load_or_create_profile(tmp_path)
    prof_path.write_text(
        '{"version":1,"mode":"remote","remote":{"enabled":true,'
        '"database_url":"postgresql+psycopg://u:p@127.0.0.1:5432/xcagi"}}',
        encoding="utf-8",
    )
    local_url = sqlite_database_url(tmp_path)
    apply_database_profile_to_env(tmp_path, local_sqlite_url=local_url)
    assert os.environ["DATABASE_URL"].startswith("postgresql")
    assert os.environ.get("XCAGI_DESKTOP_KEEP_DATABASE_URL") == "1"


def test_ensure_desktop_dirs_creates_expected_layout(tmp_path):
    dirs = ensure_desktop_dirs(tmp_path)

    assert dirs["data"].is_dir()
    assert dirs["uploads"].is_dir()
    assert dirs["logs"].is_dir()
    assert dirs["mods"].is_dir()
    assert dirs["models"].is_dir()


def test_model_manifest_loads_assets(tmp_path):
    manifest = tmp_path / "models.json"
    manifest.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "name": "demo",
                        "version": "1.0.0",
                        "url": "https://models.example/demo.bin",
                        "sha256": "0" * 64,
                        "size": 12,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assets = load_manifest(manifest)

    assert assets[0].name == "demo"
    assert assets[0].version == "1.0.0"
