#!/usr/bin/env python3
"""Sync XCAGI version across the 8 anchor files listed in VERSION.md."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# Paths relative to FHD repo root (this file: scripts/package/ → ../..)
REPO_ROOT = Path(__file__).resolve().parents[2]

VERSION_ANCHORS: list[dict[str, str]] = [
    {
        "key": "pyproject_root",
        "path": "pyproject.toml",
        "pattern": r'version\s*=\s*"([\d.]+)"',
        "replacement": 'version = "{version}"',
    },
    {
        "key": "pyproject_xcagi",
        "path": "XCAGI/pyproject.toml",
        "pattern": r'version\s*=\s*"([\d.]+)"',
        "replacement": 'version = "{version}"',
    },
    {
        "key": "frontend_package",
        "path": "frontend/package.json",
        "pattern": r'"version"\s*:\s*"([\d.]+)"',
        "replacement": '"version": "{version}"',
    },
    {
        "key": "desktop_package",
        "path": "desktop/package.json",
        "pattern": r'"version"\s*:\s*"([\d.]+)"',
        "replacement": '"version": "{version}"',
    },
    {
        "key": "root_package",
        "path": "package.json",
        "pattern": r'"version"\s*:\s*"([\d.]+)"',
        "replacement": '"version": "{version}"',
    },
    {
        "key": "fastapi_factory",
        "path": "app/fastapi_app/factory.py",
        "pattern": r'version="([\d.]+)"',
        "replacement": 'version="{version}"',
    },
    {
        "key": "mod_manifest",
        "path": "app/infrastructure/mods/manifest.py",
        "pattern": r'current_version\s*=\s*"([\d.]+)"',
        "replacement": 'current_version = "{version}"',
    },
    {
        "key": "version_md",
        "path": "VERSION.md",
        "pattern": r"`([\d.]+)`",
        "replacement": "`{version}`",
    },
]


def sync_version_anchors(
    project_root: Path,
    new_version: str,
    *,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for anchor in VERSION_ANCHORS:
        full_path = project_root / anchor["path"]
        entry: dict[str, Any] = {"key": anchor["key"], "path": anchor["path"]}
        if not full_path.is_file():
            entry.update(status="skipped", reason="file not found")
            results.append(entry)
            continue
        content = full_path.read_text(encoding="utf-8")
        if anchor["key"] == "version_md":
            lines = content.splitlines(keepends=True)
            changed = False
            new_lines: list[str] = []
            for line in lines:
                if re.search(r"\|\s*`[\d.]+`\s*\|", line):
                    current = re.search(r"`([\d.]+)`", line)
                    if current and current.group(1) == new_version:
                        new_lines.append(line)
                        continue
                    new_line, n = re.subn(r"`([\d.]+)`", f"`{new_version}`", line, count=1)
                    if n:
                        changed = True
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            if not changed:
                entry.update(status="skipped", reason="VERSION.md table versions unchanged")
            elif dry_run:
                entry.update(status="would_update", new=new_version)
            else:
                full_path.write_text("".join(new_lines), encoding="utf-8")
                entry.update(status="updated", new=new_version)
            results.append(entry)
            continue
        match = re.search(anchor["pattern"], content)
        if not match:
            entry.update(status="skipped", reason="version pattern not found")
            results.append(entry)
            continue
        old_version = match.group(1)
        if old_version == new_version:
            entry.update(status="already_synced", old=old_version)
            results.append(entry)
            continue
        replacement = anchor["replacement"].format(version=new_version)
        new_content = re.sub(anchor["pattern"], replacement, content, count=1)
        if dry_run:
            entry.update(status="would_update", old=old_version, new=new_version)
        else:
            full_path.write_text(new_content, encoding="utf-8")
            entry.update(status="updated", old=old_version, new=new_version)
        results.append(entry)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Target semver, e.g. 9.0.1")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print planned updates without writing files"
    )
    args = parser.parse_args(argv)
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        print(f"invalid version: {args.version!r} (expected major.minor.patch)", file=sys.stderr)
        return 2
    results = sync_version_anchors(REPO_ROOT, args.version, dry_run=args.dry_run)
    updated = sum(1 for r in results if r.get("status") in ("updated", "would_update"))
    for row in results:
        print(f"{row['path']}: {row.get('status', '?')}")
    print(f"anchors touched: {updated}/{len(VERSION_ANCHORS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
