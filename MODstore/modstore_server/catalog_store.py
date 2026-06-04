"""公网 Catalog 本地 JSON 存储（首期无数据库）。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

_lock = threading.Lock()


def norm_pkg_id(value: object) -> str:
    """Normalize package id for index lookups."""
    return str(value or "").strip().lower()


def norm_version(value: object) -> str:
    """Normalize semver / version string."""
    return str(value or "").strip()


def default_catalog_dir() -> Path:
    raw = (os.environ.get("MODSTORE_CATALOG_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "catalog_data"


def packages_path() -> Path:
    d = default_catalog_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "packages.json"


def files_dir() -> Path:
    d = default_catalog_dir() / "files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_store() -> Dict[str, Any]:
    p = packages_path()
    if not p.is_file():
        return {"packages": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("packages"), list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"packages": []}


def save_store(data: Dict[str, Any]) -> None:
    p = packages_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_packages(
    *,
    artifact: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    with _lock:
        rows = list(load_store().get("packages") or [])
    total = len(rows)
    if artifact:
        rows = [r for r in rows if str(r.get("artifact") or "mod") == artifact]
    if q:
        ql = q.lower()
        rows = [
            r
            for r in rows
            if ql in str(r.get("name", "")).lower()
            or ql in str(r.get("id", "")).lower()
            or ql in str(r.get("description", "")).lower()
        ]
    rows = rows[offset : offset + max(1, min(limit, 500))]
    return rows, total


def get_package(id_: str, version: str) -> Dict[str, Any] | None:
    id_ = (id_ or "").strip()
    version = (version or "").strip()
    with _lock:
        for r in load_store().get("packages") or []:
            if str(r.get("id")) == id_ and str(r.get("version")) == version:
                return dict(r)
    return None


def append_package(record: Dict[str, Any], src_file: Path | None) -> Dict[str, Any]:
    """写入记录；若提供 src_file 则复制到 files/ 并填写 download_path / sha256。"""
    pid = str(record.get("id") or "").strip()
    ver = str(record.get("version") or "").strip()
    if not pid or not ver:
        raise ValueError("id 与 version 必填")

    rec = dict(record)
    rec.setdefault("artifact", "mod")
    rec.setdefault(
        "commerce",
        {"mode": "free", "product_id": None, "sku": None},
    )
    rec.setdefault("license", {"type": "none", "verify_url": None})

    if src_file is not None and src_file.is_file():
        fd = files_dir()
        ext = src_file.suffix.lower() or ".xcmod"
        dest = fd / f"{pid}-{ver}{ext}"
        shutil.copy2(src_file, dest)
        rec["sha256"] = sha256_file(dest)
        rec["file_size"] = dest.stat().st_size
        rec["stored_filename"] = dest.name

    with _lock:
        data = load_store()
        pkgs = [x for x in data.get("packages") or [] if not (str(x.get("id")) == pid and str(x.get("version")) == ver)]
        pkgs.append(rec)
        data["packages"] = pkgs
        save_store(data)
    return rec
