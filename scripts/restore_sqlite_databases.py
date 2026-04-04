#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从备份目录或单个 .db 文件恢复 XCAGI 本地 SQLite 数据。

开发环境数据目录 = 项目根目录（与 app.utils.path_utils.get_app_data_dir 一致）。
打包环境数据目录 = %APPDATA%\\XCAGI。

用法示例：
  cd XCAGI
  .venv\\Scripts\\python scripts/restore_sqlite_databases.py --from "D:\\backups\\xcagi_20260101"
  .venv\\Scripts\\python scripts/restore_sqlite_databases.py --from "D:\\old\\products.db" --as products.db
  .venv\\Scripts\\python scripts/restore_sqlite_databases.py --from-appdata   # 从本机打包版目录拉取到当前开发目录

恢复前会把当前目标目录下将被覆盖的同名库复制到 <数据目录>/db_backup_before_restore_<时间戳>/。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db.init_db import DEFAULT_DB_FILES, get_db_path  # type: ignore
from app.utils.path_utils import get_app_data_dir, get_base_dir  # type: ignore

# 与业务相关的常见库（DEFAULT_DB_FILES + users）
_EXTRA_DB = ("users.db",)


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _safe_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _backup_if_exists(path: Path, backup_root: Path) -> None:
    if not path.is_file():
        return
    rel = path.name
    _safe_copy(path, backup_root / rel)


def restore_from_file(source: Path, dest_name: str, backup_root: Path) -> list[str]:
    if not source.is_file():
        raise FileNotFoundError(f"不是文件或不存在: {source}")
    dest = Path(get_db_path(dest_name))
    _backup_if_exists(dest, backup_root)
    _safe_copy(source, dest)
    return [f"{source} -> {dest}"]


def restore_from_directory(source_dir: Path, backup_root: Path, include_units: bool) -> list[str]:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"不是目录或不存在: {source_dir}")
    log: list[str] = []
    names = list(dict.fromkeys(list(DEFAULT_DB_FILES) + list(_EXTRA_DB)))
    for name in names:
        cand = source_dir / name
        if cand.is_file():
            dest = Path(get_db_path(name))
            _backup_if_exists(dest, backup_root)
            _safe_copy(cand, dest)
            log.append(f"{cand} -> {dest}")

    if include_units:
        src_units = source_dir / "unit_databases"
        if src_units.is_dir():
            dst_units = Path(get_base_dir()) / "unit_databases"
            # 先备份整个现有目录（若存在）
            if dst_units.is_dir():
                bak = backup_root / f"unit_databases_existing_{_timestamp()}"
                shutil.copytree(dst_units, bak)
                log.append(f"已备份现有 unit_databases -> {bak}")
            if dst_units.exists():
                shutil.rmtree(dst_units)
            shutil.copytree(src_units, dst_units)
            log.append(f"{src_units} -> {dst_units}")

    return log


def restore_from_appdata(backup_root: Path, include_units: bool) -> list[str]:
    app_data = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if not app_data:
        raise RuntimeError("未找到 APPDATA/LOCALAPPDATA，无法定位打包版数据目录")
    packaged = Path(app_data) / "XCAGI"
    if not packaged.is_dir():
        raise FileNotFoundError(f"打包版数据目录不存在: {packaged}")
    return restore_from_directory(packaged, backup_root, include_units=include_units)


def main() -> int:
    parser = argparse.ArgumentParser(description="从备份恢复 XCAGI SQLite 数据库")
    parser.add_argument(
        "--from",
        dest="source",
        metavar="PATH",
        help="备份目录，或单个 .db 文件",
    )
    parser.add_argument(
        "--as",
        dest="dest_name",
        metavar="FILENAME",
        default="products.db",
        help="当 --from 为单个文件时，写入数据目录下的文件名（默认 products.db）",
    )
    parser.add_argument(
        "--from-appdata",
        action="store_true",
        help="从 %%APPDATA%%\\XCAGI 复制（用于把打包版数据拉回开发目录）",
    )
    parser.add_argument(
        "--no-unit-databases",
        action="store_true",
        help="从目录恢复时不复制 unit_databases 子目录",
    )
    args = parser.parse_args()

    backup_root = Path(get_app_data_dir()) / f"db_backup_before_restore_{_timestamp()}"
    backup_root.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    try:
        if args.from_appdata:
            lines.extend(restore_from_appdata(backup_root, include_units=not args.no_unit_databases))
        elif args.source:
            src = Path(os.path.expandvars(os.path.expanduser(args.source))).resolve()
            if src.is_file():
                lines.extend(restore_from_file(src, args.dest_name, backup_root))
            elif src.is_dir():
                lines.extend(
                    restore_from_directory(
                        src,
                        backup_root,
                        include_units=not args.no_unit_databases,
                    )
                )
            else:
                raise FileNotFoundError(f"路径不存在: {src}")
        else:
            parser.error("请指定 --from <路径> 或 --from-appdata")

        if not lines:
            print(
                "未复制任何文件：备份中未找到可识别的库文件（"
                + ", ".join(DEFAULT_DB_FILES)
                + ", users.db）。",
                file=sys.stderr,
            )
            print(f"若曾备份到其他路径，请将整目录作为 --from 参数。", file=sys.stderr)
            return 2

        print(f"预备份目录（本次被覆盖前的文件）: {backup_root}")
        for line in lines:
            print(line)
        print("完成。请重启后端再打开前端。")
        return 0
    except Exception as e:
        print(f"失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
