from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.shell import mod_database_gate


def test_gate_open_when_no_requirement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FHD_DB_MOD_GATE", raising=False)
    assert mod_database_gate.mod_db_gate_open() is True


def test_gate_closed_raises_in_get_database_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FHD_DB_MOD_GATE", "missing-mod-xyz")
    p = tmp_path / "mods.json"
    p.write_text(
        json.dumps(
            [
                {"id": "all", "name": "全部", "type": "category", "color": None},
                {"id": "other", "name": "O", "type": "template", "color": "green"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FHD_SHELL_MODS_JSON", str(p))
    from backend import database

    database.dispose_sync_engine()
    with pytest.raises(RuntimeError, match="database_mod_gate_closed"):
        database.get_database_url()


def test_get_db_status_when_gate_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FHD_DB_MOD_GATE", "missing-mod-xyz")
    p = tmp_path / "mods.json"
    p.write_text(
        json.dumps(
            [{"id": "all", "name": "全部", "type": "category", "color": None}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FHD_SHELL_MODS_JSON", str(p))
    from backend import database

    database.dispose_sync_engine()
    st = database.get_db_status()
    assert st.get("database_mod_gate_closed") is True
    assert st.get("mod_database_gate", {}).get("gate_open") is False
