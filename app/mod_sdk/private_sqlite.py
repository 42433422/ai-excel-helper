"""Mod 自有 SQLite 文件路径（与主库拆分后的 ``data/`` 根对齐）。

主应用按 Mod 拆主业务库时走 ``DATABASE_URL`` + ``products__<mod>.db``（见 ``app.db``）。
扩展若另有独立 sqlite（如考勤侧库），应落在同一数据根下的 ``mod_dbs/``，
避免桌面模式或子目录启动时写到错误目录。
"""

from __future__ import annotations

import os
from pathlib import Path


def _find_existing_mod_db_in_workspace(filename: str) -> Path | None:
    """在 cwd 向上查找已存在的 data/mod_dbs/<filename>。"""
    name = (filename or "").strip()
    if not name:
        return None
    candidate = Path(os.getcwd()).resolve()
    for _ in range(8):
        hit = candidate / "data" / "mod_dbs" / name
        if hit.is_file():
            return hit
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return None


def resolve_mod_private_sqlite_path(filename: str) -> Path:
    """解析 ``<数据根>/mod_dbs/<filename>``，并确保目录存在。

    优先级（与 ``get_app_data_dir`` / 桌面引导一致）：

    1. ``DATABASE_PATH`` — 桌面下为主 ``data`` 目录，侧库为 ``<DATABASE_PATH>/mod_dbs/``。
    2. ``XCAGI_DATA_DIR`` / ``XCAGI_DESKTOP_DATA_DIR`` — 用户数据根，侧库为 ``<根>/data/mod_dbs/``。
    3. ``XCAGI_WORKSPACE_ROOT`` / ``WORKSPACE_ROOT`` — 工作区根，侧库为 ``<根>/data/mod_dbs/``。
    4. 自 ``cwd`` 向上最多 6 层，若已存在 ``data/mod_dbs/<filename>`` 则选用该工作区根。
    5. ``get_data_dir()/mod_dbs`` — 与主 SQLite 母库目录一致（开发态常见）。
    6. 回退 ``cwd/data/mod_dbs``。
    """
    name = (filename or "").strip()
    if not name:
        raise ValueError("resolve_mod_private_sqlite_path: empty filename")

    dp = (os.environ.get("DATABASE_PATH") or "").strip()
    if dp:
        db_dir = Path(dp).resolve() / "mod_dbs"
        candidate = db_dir / name
        if candidate.is_file():
            return candidate
        # 桌面 data 根尚无侧库时，回退到工作区内已有 mod_dbs（避免空库盖住开发数据）
        fallback = _find_existing_mod_db_in_workspace(name)
        if fallback is not None:
            return fallback
        db_dir.mkdir(parents=True, exist_ok=True)
        return candidate

    data_root = (os.environ.get("XCAGI_DATA_DIR") or "").strip() or (
        os.environ.get("XCAGI_DESKTOP_DATA_DIR") or ""
    ).strip()
    if data_root:
        base = Path(data_root).resolve()
        db_dir = base / "data" / "mod_dbs"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / name

    wr = (os.environ.get("XCAGI_WORKSPACE_ROOT") or "").strip()
    if wr:
        base_path = Path(wr).resolve()
    else:
        ws = (os.environ.get("WORKSPACE_ROOT") or "").strip()
        if ws:
            base_path = Path(ws).resolve()
        else:
            candidate = Path(os.getcwd()).resolve()
            found: Path | None = None
            for _ in range(6):
                if (candidate / "data" / "mod_dbs" / name).exists():
                    found = candidate
                    break
                parent = candidate.parent
                if parent == candidate:
                    break
                candidate = parent
            if found is not None:
                base_path = found
            else:
                try:
                    from app.utils.path_utils import get_data_dir

                    db_dir = Path(get_data_dir()).resolve() / "mod_dbs"
                    db_dir.mkdir(parents=True, exist_ok=True)
                    return db_dir / name
                except Exception:
                    base_path = Path(os.getcwd()).resolve()

    db_dir = base_path / "data" / "mod_dbs"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / name


__all__ = ["resolve_mod_private_sqlite_path"]
