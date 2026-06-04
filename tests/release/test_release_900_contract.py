"""Release contract tests (isolated conftest via --confcutdir=tests/release)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_files_exist() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    for name in ("release-desktop.yml", "release-web.yml", "release-android.yml"):
        assert (workflows / name).is_file(), f"missing {name}"


def test_dual_sku_packaging_scripts_exist() -> None:
    scripts = REPO_ROOT / "scripts" / "package"
    assert (scripts / "stage-sku-download-folders.ps1").is_file()
    assert (scripts / "build-android-release-signed.ps1").is_file()


def test_sync_version_anchors_script_present() -> None:
    script = REPO_ROOT / "scripts" / "package" / "sync-version-anchors.py"
    assert script.is_file()


def test_release_train_json_exists_and_quad() -> None:
    import json

    path = REPO_ROOT / "config" / "release_train.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    quad = str(data.get("current") or data.get("release_train") or "").strip()
    parts = quad.split(".")
    assert len(parts) == 4
    assert all(p.isdigit() for p in parts)


def test_xiaomi_store_listing_stub_exists() -> None:
    listing = REPO_ROOT / "config" / "store_listing" / "xiaomi.yaml"
    assert listing.is_file()
    text = listing.read_text(encoding="utf-8")
    assert "store: xiaomi" in text
    assert "beian.miit.gov.cn" in text
