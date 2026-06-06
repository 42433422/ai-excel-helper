"""Catalog /v1 路由冒烟（内存临时目录）。"""

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")


def _isolate_catalog_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODSTORE_DB_PATH", str(tmp_path / "modstore.db"))
    from modstore_server.models import init_db, reset_session_factory

    reset_session_factory()
    init_db()


def test_catalog_index_empty(monkeypatch, tmp_path: Path):
    _isolate_catalog_db(monkeypatch, tmp_path)
    monkeypatch.setenv("MODSTORE_CATALOG_DIR", str(tmp_path))
    from modstore_server.catalog_store import load_store, save_store

    save_store({"packages": []})
    from fastapi.testclient import TestClient
    from modstore_server.app import app

    c = TestClient(app)
    r = c.get("/v1/index.json")
    assert r.status_code == 200
    assert r.json() == {"packages": []}


def test_catalog_upload_with_token(monkeypatch, tmp_path: Path):
    _isolate_catalog_db(monkeypatch, tmp_path)
    monkeypatch.setenv("MODSTORE_CATALOG_DIR", str(tmp_path))
    monkeypatch.setenv("MODSTORE_CATALOG_UPLOAD_TOKEN", "secret-test")
    from modstore_server.catalog_store import save_store

    save_store({"packages": []})

    from fastapi.testclient import TestClient
    from modstore_server.app import app

    # 最小 zip：含 manifest.json（mod）
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "id": "catalog-test-mod",
                    "name": "Test",
                    "version": "0.0.1",
                    "artifact": "mod",
                    "backend": {"entry": "blueprints", "init": "mod_init"},
                    "frontend": {"routes": "routes"},
                },
                ensure_ascii=False,
            ),
        )
        zf.writestr("backend/blueprints.py", "# stub\n")
        zf.writestr("backend/mod_init.py", "def mod_init():\n    pass\n")
        zf.writestr("frontend/routes.js", "export default []\n")
    buf.seek(0)

    c = TestClient(app)
    meta = json.dumps(
        {
            "id": "catalog-test-mod",
            "version": "0.0.1",
            "name": "Test",
            "artifact": "mod",
        },
        ensure_ascii=False,
    )
    r = c.post(
        "/v1/packages",
        headers={"Authorization": "Bearer secret-test"},
        data={"metadata": meta},
        files={"file": ("catalog-test-mod-0.0.1.xcmod", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    idx = c.get("/v1/index.json").json()
    # 仅登记到 packages.json、未在市场上架时，公网 index 不应暴露
    assert idx["packages"] == []

    from modstore_server.db import get_session_factory
    from modstore_server.models import CatalogItem

    sf = get_session_factory()
    with sf() as session:
        row = session.query(CatalogItem).filter(CatalogItem.pkg_id == "catalog-test-mod").first()
        if row:
            row.is_public = True
            session.commit()
    idx = c.get("/v1/index.json").json()
    assert len(idx["packages"]) == 1
    assert idx["packages"][0]["id"] == "catalog-test-mod"
    assert idx["packages"][0].get("public_listing") is True


def test_catalog_upload_blocked_when_employee_gate_on(monkeypatch, tmp_path: Path):
    _isolate_catalog_db(monkeypatch, tmp_path)
    monkeypatch.setenv("MODSTORE_CATALOG_DIR", str(tmp_path))
    monkeypatch.setenv("MODSTORE_CATALOG_UPLOAD_TOKEN", "secret-test")
    monkeypatch.setenv("MODSTORE_CATALOG_REQUIRE_EMPLOYEE_SANDBOX", "1")
    from modstore_server.catalog_store import save_store

    save_store({"packages": []})

    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "bad-mod/manifest.json",
            json.dumps(
                {
                    "id": "bad-mod",
                    "name": "B",
                    "version": "0.0.1",
                    "artifact": "mod",
                    "backend": {"entry": "blueprints", "init": "mod_init"},
                    "frontend": {"routes": "routes"},
                    "workflow_employees": [{"id": "h1", "label": "H"}],
                },
                ensure_ascii=False,
            ),
        )
        zf.writestr("bad-mod/backend/blueprints.py", "# no stub mount\n")
    buf.seek(0)

    from fastapi.testclient import TestClient
    from modstore_server.app import app

    c = TestClient(app)
    meta = json.dumps(
        {"id": "bad-mod", "version": "0.0.1", "name": "B", "artifact": "mod"},
        ensure_ascii=False,
    )
    r = c.post(
        "/v1/packages",
        headers={"Authorization": "Bearer secret-test"},
        data={"metadata": meta},
        files={"file": ("bad-mod-0.0.1.xcmod", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 400, r.text
    assert "员工沙箱" in r.text or "沙箱" in r.text


def test_catalog_upload_passes_employee_gate_with_stubs(monkeypatch, tmp_path: Path):
    _isolate_catalog_db(monkeypatch, tmp_path)
    monkeypatch.setenv("MODSTORE_CATALOG_DIR", str(tmp_path))
    monkeypatch.setenv("MODSTORE_CATALOG_UPLOAD_TOKEN", "secret-test")
    monkeypatch.setenv("MODSTORE_CATALOG_REQUIRE_EMPLOYEE_SANDBOX", "1")
    from modstore_server.catalog_store import save_store

    save_store({"packages": []})

    import io
    import zipfile

    buf = io.BytesIO()
    bp = (
        "def register_fastapi_routes(app, mod_id):\n"
        "    from .employee_stubs import e_h1 as _emp_stub_e_h1\n"
        "    _emp_stub_e_h1.mount_employee_router(app, mod_id)\n"
    )
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "good-mod/manifest.json",
            json.dumps(
                {
                    "id": "good-mod",
                    "name": "G",
                    "version": "0.0.1",
                    "artifact": "mod",
                    "backend": {"entry": "blueprints", "init": "mod_init"},
                    "frontend": {"routes": "routes"},
                    "workflow_employees": [{"id": "h1", "label": "H"}],
                },
                ensure_ascii=False,
            ),
        )
        zf.writestr("good-mod/backend/blueprints.py", bp)
        zf.writestr("good-mod/backend/employee_stubs/__init__.py", "")
        zf.writestr("good-mod/backend/employee_stubs/e_h1.py", "# stub\n")
    buf.seek(0)

    from fastapi.testclient import TestClient
    from modstore_server.app import app

    c = TestClient(app)
    meta = json.dumps(
        {"id": "good-mod", "version": "0.0.1", "name": "G", "artifact": "mod"},
        ensure_ascii=False,
    )
    r = c.post(
        "/v1/packages",
        headers={"Authorization": "Bearer secret-test"},
        data={"metadata": meta},
        files={"file": ("good-mod-0.0.1.xcmod", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 200, r.text
