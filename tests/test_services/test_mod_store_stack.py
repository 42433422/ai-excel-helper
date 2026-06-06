"""MOD 商店迁移栈：catalog_client、zip 规范化、路由装配。"""

from __future__ import annotations

import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.fastapi_routes.mod_store_routes import router as mod_store_router
from app.services import catalog_client
from app.services.mod_zip_normalize import normalize_package_zip_path


def test_catalog_base_url_default():
    assert catalog_client.catalog_base_url().startswith("http")


def test_normalize_package_zip_passes_through_when_manifest_at_root(tmp_path: Path):
    zpath = tmp_path / "m.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("manifest.json", "{}")
        zf.writestr("readme.txt", b"x")
    assert normalize_package_zip_path(str(zpath)) == str(zpath)


def test_normalize_package_zip_flattens_single_top_folder(tmp_path: Path):
    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("myid/manifest.json", "{}")
        zf.writestr("myid/foo.txt", b"hi")
    out = normalize_package_zip_path(str(inner))
    assert out != str(inner)
    with zipfile.ZipFile(out, "r") as zf2:
        names = set(zf2.namelist())
    assert "manifest.json" in names
    Path(out).unlink(missing_ok=True)


def test_mod_store_catalog_mount(monkeypatch: pytest.MonkeyPatch):
    async def _empty_remote():
        if False:  # pragma: no cover
            yield {}

    monkeypatch.setattr(
        "app.fastapi_routes.mod_store_routes.iter_catalog_packages",
        _empty_remote,
    )

    app = FastAPI()
    app.include_router(mod_store_router, prefix="/api/mod-store")
    client = TestClient(app)
    r = client.get("/api/mod-store/catalog")
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body
    assert "installed" in body["data"]
    assert "available" in body["data"]
