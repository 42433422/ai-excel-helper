# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-office-employee-pack-bridge"


def test_office_catalog_file():
    data = json.loads((MOD_DIR / "config" / "office_pack_catalog.json").read_text(encoding="utf-8"))
    assert len(data.get("pack_ids") or []) == 10


def test_list_office_pack_catalog():
    from app.mod_sdk.employee_pack_compat import list_office_pack_catalog

    cat = list_office_pack_catalog()
    assert cat.get("pack_count") == 10
    assert cat["entries"][0].get("format") in ("excel", "csv", "pdf", "ppt", "word", "other")


def test_decoupling_progress_payload():
    from app.mod_sdk.decoupling_progress import build_decoupling_progress_payload

    data = build_decoupling_progress_payload(["xcagi-erp-domain-bridge"])
    assert data.get("milestones_total", 0) >= 8
    assert "bridges" in data
    assert "employee_pack" in (data.get("bridges") or {})
