from __future__ import annotations

from fastapi.testclient import TestClient

from app.fastapi_app import create_fastapi_app


def test_mods_list_supports_etag_304():
    client = TestClient(create_fastapi_app())
    first = client.get("/api/mods/")
    assert first.status_code == 200, first.text
    etag = first.headers.get("etag") or first.headers.get("ETag")
    assert etag
    second = client.get("/api/mods/", headers={"If-None-Match": etag})
    assert second.status_code == 304
