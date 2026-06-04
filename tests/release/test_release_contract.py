"""Release train / version anchor contract smoke (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.release_gate

_REPO = Path(__file__).resolve().parents[2]
_RELEASE_TRAIN = _REPO / "config" / "release_train.json"


def test_release_train_json_exists_and_quad() -> None:
    assert _RELEASE_TRAIN.is_file(), "config/release_train.json missing"
    data = json.loads(_RELEASE_TRAIN.read_text(encoding="utf-8"))
    quad = str(data.get("current") or data.get("release_train") or "").strip()
    parts = quad.split(".")
    assert len(parts) == 4, f"expected quad version, got {quad!r}"
    assert all(p.isdigit() for p in parts)


def test_sync_version_anchors_script_present() -> None:
    script = _REPO / "scripts" / "package" / "sync-version-anchors.py"
    assert script.is_file(), "scripts/package/sync-version-anchors.py missing"
