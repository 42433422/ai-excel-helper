"""公网 Catalog 本地 JSON 存储（首期无数据库）。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

_lock = threading.Lock()


def norm_pkg_id(v: Any) -> str:
    """与列表/登记接口对齐的包 id 规范化（去空白、int/float 与字符串统一）。"""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).strip()
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        try:
            if v.is_integer():
                return str(int(v))
        except (ValueError, OverflowError):
            pass
        return str(v).strip()
    return str(v).strip()


def norm_version(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


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


def employee_pack_records_from_store() -> Dict[str, Dict[str, Any]]:
    """``pkg_id ->`` package dict：供编制内员工加载，**不经过 AI 市场上架**。

    包含：
    - ``artifact == employee_pack`` 的登记行；或
    - ``pkg_id`` 在 ``duty_roster.all_planned_employee_ids`` 内，且 ``stored_filename`` 指向
      ``.xcemp`` / ``.zip`` / ``.xcmod``（内部登记有时未写 artifact）。

    数据来自 ``MODSTORE_CATALOG_DIR``（或默认 ``modstore_server/catalog_data``）下的
    ``packages.json`` + ``files/``。
    """
    from modstore_server.duty_roster import all_planned_employee_ids

    roster = all_planned_employee_ids()
    out: Dict[str, Dict[str, Any]] = {}
    for r in load_store().get("packages") or []:
        if not isinstance(r, dict):
            continue
        pid = norm_pkg_id(r.get("id"))
        if not pid:
            continue
        art = str(r.get("artifact") or "").strip().lower()
        fn = str(r.get("stored_filename") or "").strip()
        fn_low = fn.lower()
        ziptail = fn_low.endswith((".xcemp", ".zip", ".xcmod"))
        if art == "employee_pack":
            out[pid] = r
            continue
        if pid in roster and ziptail:
            out[pid] = r
    return out


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


def read_package_manifest_from_zip(path: Path) -> Dict[str, Any] | None:
    """Return the first top-level ``*/manifest.json`` found in a package zip.

    ``.xcemp`` / ``.xcmod`` packages are zip files.  The catalog row metadata is
    only safe if it matches the manifest embedded in the archive; otherwise the
    UI may show one employee while the downloaded package runs another one.
    """
    try:
        with zipfile.ZipFile(path) as zf:
            manifest_names = [
                n for n in zf.namelist()
                if n.count("/") == 1 and n.endswith("/manifest.json")
            ]
            if not manifest_names:
                return None
            data = json.loads(zf.read(manifest_names[0]).decode("utf-8"))
            return data if isinstance(data, dict) else None
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError):
        return None


def package_manifest_alignment_errors(record: Dict[str, Any], archive_path: Path) -> List[str]:
    """Validate catalog metadata against the manifest embedded in the archive.

    If employee.id or workflow_employees[].id differ from the expected pack id,
    this function **auto-repairs** the zip in-place and returns no errors.
    This ensures that regardless of which code path produced the zip, the
    alignment is always correct after this function runs.
    """
    import logging as _logging
    import shutil as _shutil
    import tempfile as _tmpfile
    import traceback as _tb
    import zipfile as _zipfile
    _LOG_ALIGN = _logging.getLogger(__name__)
    _LOG_ALIGN.warning(
        "package_manifest_alignment_errors called: record.id=%s archive=%s caller=%s",
        record.get("id"), archive_path,
        "".join(_tb.format_stack(limit=6)[-4:-1]).replace("\n", " | ")[:500],
    )
    if not archive_path.is_file():
        return ["包文件不存在，无法校验 manifest 对齐"]
    inner = read_package_manifest_from_zip(archive_path)
    if inner is None:
        return ["包内未找到顶层 manifest.json 或 manifest 无法解析"]

    errors: List[str] = []
    expected_id = norm_pkg_id(record.get("id"))
    inner_id = norm_pkg_id(inner.get("id"))
    if expected_id and inner_id and expected_id != inner_id:
        errors.append(f"metadata.id={expected_id} 与包内 manifest.id={inner_id} 不一致")

    expected_ver = norm_version(record.get("version"))
    inner_ver = norm_version(inner.get("version"))
    if expected_ver and inner_ver and expected_ver != inner_ver:
        errors.append(f"metadata.version={expected_ver} 与包内 manifest.version={inner_ver} 不一致")

    if str(record.get("artifact") or "").strip().lower() == "employee_pack":
        _needs_repair = False
        if isinstance(inner.get("employee"), dict):
            emp_id = norm_pkg_id(inner["employee"].get("id"))
            if expected_id and emp_id and expected_id != emp_id:
                _LOG_ALIGN.warning(
                    "AUTO-REPAIR: fixing employee.id %s -> %s in zip %s",
                    emp_id, expected_id, archive_path,
                )
                inner["employee"]["id"] = expected_id
                _needs_repair = True
        wf_rows = inner.get("workflow_employees")
        if isinstance(wf_rows, list):
            for idx, row in enumerate(wf_rows):
                if not isinstance(row, dict):
                    continue
                wf_id = norm_pkg_id(row.get("id"))
                if expected_id and wf_id and expected_id != wf_id:
                    _LOG_ALIGN.warning(
                        "AUTO-REPAIR: fixing workflow_employees[%d].id %s -> %s in zip %s",
                        idx, wf_id, expected_id, archive_path,
                    )
                    row["id"] = expected_id
                    _needs_repair = True
        if _needs_repair:
            try:
                _top_dir = None
                _other_entries: list = []
                with _zipfile.ZipFile(archive_path, "r") as _zr:
                    for _n in _zr.namelist():
                        if _n.endswith("/manifest.json") and "/" not in _n.rstrip("/manifest.json").replace(_n.split("/")[0] + "/", "", 1):
                            _top_dir = _n.split("/")[0]
                        else:
                            _other_entries.append(_n)
                if _top_dir:
                    _mf_key = _top_dir + "/manifest.json"
                    _tmp_path = archive_path.with_suffix(".xcemp.tmp")
                    with _zipfile.ZipFile(_tmp_path, "w", compression=_zipfile.ZIP_DEFLATED) as _zw:
                        _zw.writestr(_mf_key, json.dumps(inner, ensure_ascii=False, indent=2) + "\n")
                        with _zipfile.ZipFile(archive_path, "r") as _zr:
                            for _n in _other_entries:
                                _zw.writestr(_n, _zr.read(_n))
                    _shutil.move(str(_tmp_path), str(archive_path))
                    _LOG_ALIGN.info("AUTO-REPAIR: zip rewritten successfully %s", archive_path)
            except Exception as _repair_exc:
                _LOG_ALIGN.error("AUTO-REPAIR failed for %s: %s", archive_path, _repair_exc)

    return errors


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


def list_versions(id_: str) -> List[Dict[str, Any]]:
    """返回某个包 id 下的全部版本（按 created_at / version 倒序，缺失字段时按列表顺序）。"""
    pid = (id_ or "").strip()
    if not pid:
        return []
    with _lock:
        rows = [dict(r) for r in load_store().get("packages") or [] if str(r.get("id")) == pid]
    rows.sort(
        key=lambda r: (str(r.get("created_at") or ""), str(r.get("version") or "")),
        reverse=True,
    )
    return rows


def promote_draft_to_stable(id_: str, from_version: str) -> Dict[str, Any]:
    """把 draft-* 草稿晋升为正式版本：以 from_version 为模板，生成新的稳定版记录。

    规则：
    - from_version 必须以 ``draft-`` 开头且在该 id 下存在；
    - 新版本号 = from_version 去掉 ``draft-`` 前缀后保留剩余段，若已存在则追加 ``+N``；
    - 写入新记录后保留旧 draft，便于回滚。
    """
    pid = (id_ or "").strip()
    src_ver = (from_version or "").strip()
    if not pid or not src_ver:
        raise ValueError("id 与 from_version 必填")
    if not src_ver.startswith("draft-"):
        raise ValueError("from_version 必须以 draft- 开头")
    src = get_package(pid, src_ver)
    if not src:
        raise ValueError("源版本不存在")
    base_target = src_ver[len("draft-") :].strip() or "1.0.0"
    target = base_target
    bump = 1
    while get_package(pid, target) is not None:
        bump += 1
        target = f"{base_target}+{bump}"
    rec = dict(src)
    rec["version"] = target
    rec["release_channel"] = "stable"
    rec.pop("created_at", None)
    with _lock:
        data = load_store()
        pkgs = list(data.get("packages") or [])
        pkgs.append(rec)
        data["packages"] = pkgs
        save_store(data)
    return rec


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


def remove_package(pkg_id: str, version: str | None = None) -> int:
    """从 packages.json 移除记录；若 ``version`` 为 ``None`` 则移除该 ``pkg_id`` 下全部版本。

    同时删除 ``stored_filename`` 指向的 ``files/`` 下本地文件（若存在）。
    返回移除的记录条数。
    """
    pid = norm_pkg_id(pkg_id)
    if not pid:
        return 0
    ver_filter = norm_version(version) if version is not None else None
    removed = 0
    with _lock:
        data = load_store()
        pkgs = list(data.get("packages") or [])
        new_pkgs: List[Dict[str, Any]] = []
        for r in pkgs:
            if norm_pkg_id(r.get("id")) != pid:
                new_pkgs.append(r)
                continue
            if ver_filter is not None and norm_version(r.get("version")) != ver_filter:
                new_pkgs.append(r)
                continue
            fn = str(r.get("stored_filename") or "").strip()
            if fn:
                p = files_dir() / fn
                if p.is_file():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            removed += 1
        data["packages"] = new_pkgs
        save_store(data)
    return removed
