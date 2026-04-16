from __future__ import annotations

from backend.database import postgresql_connection_summary


def test_postgresql_connection_summary_parses_db_and_host() -> None:
    s = postgresql_connection_summary("postgresql+psycopg://u:secret@host.example:5544/appdb")
    assert s["database_name"] == "appdb"
    assert s["host_port"] == "host.example:5544"
    assert "***" in s["redacted_url"]


def test_mod_publish_to_xcagi_catalog_mod(client) -> None:
    r = client.post("/api/mods/%E5%AE%A2%E6%88%B7%E7%AE%A1%E7%90%86/publish-to-xcagi")
    assert r.status_code == 200
    j = r.json()
    assert j.get("success") is True
    assert j.get("data", {}).get("mod_id") == "客户管理"


def test_mod_publish_to_xcagi_unknown_mod(client) -> None:
    r = client.post("/api/mods/__definitely_missing_mod__/publish-to-xcagi")
    assert r.status_code == 200
    j = r.json()
    assert j.get("success") is False
