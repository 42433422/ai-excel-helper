"""共享 fixtures：隔离配置与库目录，避免测试污染开发者本机 .modstore-config.json。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from modman.repo_config import RepoConfig


@pytest.fixture
def isolated_modstore(tmp_path, monkeypatch):
    """
    将库根、项目根（沙箱目录父级）指向临时目录，并替换 load/save_config。
    """
    library = tmp_path / "library"
    library.mkdir(parents=True, exist_ok=True)
    project_home = tmp_path / "modstore_project"
    project_home.mkdir(parents=True, exist_ok=True)

    cfg_holder: dict[str, RepoConfig] = {
        "cfg": RepoConfig(
            library_root=str(library),
            xcagi_root="",
            xcagi_backend_url="http://test.invalid",
        )
    }

    def fake_load() -> RepoConfig:
        return cfg_holder["cfg"]

    def fake_save(c: RepoConfig) -> None:
        cfg_holder["cfg"] = c

    monkeypatch.setattr("modstore_server.app.load_config", fake_load)
    monkeypatch.setattr("modstore_server.app.save_config", fake_save)
    monkeypatch.setattr("modstore_server.app.project_root", lambda: project_home)
    monkeypatch.setattr("modman.repo_config.load_config", fake_load)
    monkeypatch.setattr("modman.repo_config.save_config", fake_save)
    monkeypatch.setattr("modman.store.project_root", lambda: project_home)
    monkeypatch.setattr("modstore_server.fhd_routes_api.load_config", fake_load)
    monkeypatch.setattr("modstore_server.fhd_routes_api.save_config", fake_save)
    monkeypatch.setattr("modstore_server.fhd_routes_api.project_root", lambda: project_home)
    monkeypatch.setattr("modstore_server.fhd_modstore_state.load_config", fake_load)
    monkeypatch.setenv("MODSTORE_DB_PATH", str(tmp_path / "modstore.db"))
    from modstore_server.models import init_db, reset_session_factory

    reset_session_factory()
    init_db()

    from modstore_server.app import app

    return {
        "client": TestClient(app),
        "library": library,
        "project_home": project_home,
        "cfg_holder": cfg_holder,
    }


@pytest.fixture
def client(isolated_modstore):
    return isolated_modstore["client"]


@pytest.fixture
def library(isolated_modstore):
    return isolated_modstore["library"]


@pytest.fixture
def project_home(isolated_modstore):
    return isolated_modstore["project_home"]
