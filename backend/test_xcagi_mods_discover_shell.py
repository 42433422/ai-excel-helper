"""manifest shell_* 解析：frontend 块与 camelCase 别名。"""

from __future__ import annotations

import json
from pathlib import Path


def test_read_manifest_dicts_shell_menu_preset_in_frontend(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "xcagi"
    mdir = root / "mods" / "hr-pro"
    mdir.mkdir(parents=True)
    manifest = {
        "id": "hr-pro",
        "name": "HR",
        "type": "mod",
        "frontend": {"routes": "frontend/routes", "shell_menu_preset": "员工管理"},
    }
    (mdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("XCAGI_ROOT", str(root))
    monkeypatch.delenv("XCAGI_MODS_DIR", raising=False)

    from backend.shell.xcagi_mods_discover import read_manifest_dicts

    rows = read_manifest_dicts()
    assert len(rows) == 1
    assert rows[0].get("shell_menu_preset") == "员工管理"


def test_read_manifest_dicts_shell_menu_preset_camel_on_root(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "xcagi2"
    mdir = root / "mods" / "cam-pro"
    mdir.mkdir(parents=True)
    manifest = {"id": "cam-pro", "name": "C", "type": "mod", "shellMenuPreset": "电商"}
    (mdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("XCAGI_ROOT", str(root))
    monkeypatch.delenv("XCAGI_MODS_DIR", raising=False)

    from backend.shell.xcagi_mods_discover import read_manifest_dicts

    rows = read_manifest_dicts()
    assert len(rows) == 1
    assert rows[0].get("shell_menu_preset") == "电商"
