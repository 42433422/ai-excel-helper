"""schema_auto_init：拆分 SQL 等纯逻辑（不依赖 PostgreSQL）；含 mods 模板路径与 manifest 相对路径。"""

from __future__ import annotations

from pathlib import Path

from backend.schema_auto_init import statements_from_init_sql


def test_statements_from_init_sql_non_empty():
    raw = """
-- c
BEGIN;

CREATE TABLE IF NOT EXISTS a (id int);

COMMIT;
"""
    sts = statements_from_init_sql(raw)
    assert len(sts) == 1
    assert "CREATE TABLE" in sts[0]


def test_repo_pg_init_includes_document_templates_seed():
    from backend.schema_auto_init import _load_init_sql_text

    sts = statements_from_init_sql(_load_init_sql_text())
    assert len(sts) >= 8
    assert any("INSERT INTO document_templates" in s for s in sts)
    assert any("purchase_units" in s for s in sts)
    assert any("products" in s and "CREATE TABLE" in s for s in sts)
    assert any("customers" in s and "CREATE TABLE" in s for s in sts)
    assert any("document_templates" in s and "CREATE TABLE" in s for s in sts)


def test_resolve_mods_storage_relpath(tmp_path, monkeypatch):
    from backend import document_template_service as dts

    xcagi = tmp_path / "xcagi"
    rel = Path("mods") / "my_mod" / "document_templates" / "a.docx"
    target = xcagi / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"PK\x03\x04fake")

    monkeypatch.setattr(
        "backend.shell.xcagi_mods_discover.xcagi_root",
        lambda: xcagi,
    )

    got = dts._resolve_storage_to_path(str(rel).replace("\\", "/"))
    assert got is not None
    assert got.resolve() == target.resolve()


def test_relpath_parts_ok_accepts_mods_prefix():
    from backend import document_template_service as dts

    assert dts._relpath_parts_ok("mods/x/document_templates/y.docx") is True
    assert dts._relpath_parts_ok("mods/x/other/y.docx") is False
    assert dts._relpath_parts_ok("424/document_templates/y.docx") is True


def test_manifest_database_seed_sql_resolved_relative_to_mod_dir(tmp_path, monkeypatch):
    from backend.shell import xcagi_mods_discover as disc

    mods = tmp_path / "mods" / "seed_demo"
    mods.mkdir(parents=True)
    sql = mods / "seeds" / "a.sql"
    sql.parent.mkdir(parents=True, exist_ok=True)
    sql.write_text("SELECT 1;", encoding="utf-8")
    (mods / "manifest.json").write_text(
        '{"id":"seed_demo","name":"S","database_seed_sql":"seeds/a.sql"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("XCAGI_MODS_DIR", str(tmp_path / "mods"))
    rows = disc.read_manifest_dicts()
    assert any(r.get("id") == "seed_demo" for r in rows)
    row = next(r for r in rows if r.get("id") == "seed_demo")
    assert Path(row["database_seed_sql"]).resolve() == sql.resolve()
