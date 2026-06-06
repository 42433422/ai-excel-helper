import pytest


def test_resolve_cors_strips_wildcard(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*,http://example.com")
    from app.fastapi_app import resolve_cors_allow_origins

    origins = resolve_cors_allow_origins()
    assert "*" not in origins
    assert "http://example.com" in origins


def test_resolve_cors_only_star_uses_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    from app.fastapi_app import resolve_cors_allow_origins

    origins = resolve_cors_allow_origins()
    assert "*" not in origins
    assert "http://127.0.0.1:5000" in origins
