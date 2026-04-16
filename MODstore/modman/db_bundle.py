"""
将 SQLite 等数据文件拷入 Mod 目录（约定子目录 ``data/``），便于随 Mod 分发与版本管理。

FHD 主后端当前为 PostgreSQL；本工具主要面向 XCAGI 仍使用本地 ``*.db`` 的场景，
或作为「数据种子」打进 Mod ZIP。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable


def _sqlite_sidecars(db_file: Path) -> list[Path]:
    """同目录下的 WAL/SHM/JOURNAL（若存在）一并迁移。"""
    out: list[Path] = []
    for suf in ("-wal", "-shm", "-journal"):
        p = Path(str(db_file) + suf)
        if p.is_file():
            out.append(p)
    return out


def _planned_paths(sub_raw: str, main: Path, sidecars: list[Path]) -> list[str]:
    sub = sub_raw.strip().strip("/").replace("\\", "/")
    names = [main.name] + [s.name for s in sidecars]
    return [f"{sub}/{n}" for n in names]


def copy_databases_into_mod(
    mod_dir: Path,
    sources: Iterable[Path],
    *,
    dest_subdir: str = "data",
    dry_run: bool = False,
) -> list[str]:
    """
    将若干文件拷入 ``<mod_dir>/<dest_subdir>/``，保持文件名；SQLite 则尝试同拷侧车文件。

    返回相对 mod 根的路径列表（POSIX 风格 ``/``）。
    """
    mod_dir = mod_dir.resolve()
    if not mod_dir.is_dir():
        raise FileNotFoundError(f"Mod 目录不存在: {mod_dir}")
    if not (mod_dir / "manifest.json").is_file():
        raise FileNotFoundError(f"缺少 manifest.json: {mod_dir / 'manifest.json'}")

    sub_raw = dest_subdir.strip().replace("\\", "/").strip("/")
    if not sub_raw or ".." in Path(sub_raw).parts or Path(sub_raw).is_absolute():
        raise ValueError(f"非法 dest_subdir: {dest_subdir!r}")
    dest_root = (mod_dir / sub_raw).resolve()
    if dest_root != mod_dir and mod_dir not in dest_root.parents:
        raise ValueError(f"dest_subdir 不能越出 Mod 根目录: {dest_subdir!r}")
    planned: list[str] = []
    seen_names: set[str] = set()

    for src in sources:
        sp = Path(src).expanduser().resolve()
        if not sp.is_file():
            raise FileNotFoundError(f"源不是文件: {sp}")
        if sp.name in seen_names:
            raise ValueError(f"重复的文件名（请合并来源）: {sp.name}")
        seen_names.add(sp.name)

        side = _sqlite_sidecars(sp) if sp.suffix.lower() == ".db" else []
        planned.extend(_planned_paths(sub_raw, sp, side))

        if dry_run:
            continue

        dest_root.mkdir(parents=True, exist_ok=True)
        dest_file = dest_root / sp.name
        shutil.copy2(sp, dest_file)
        for side in side:
            shutil.copy2(side, dest_root / side.name)

    if not dry_run:
        readme = dest_root / "MODMAN_DATABASE_README.txt"
        dest_root.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "\n".join(
                [
                    "本目录由「modman migrate-db-into-mod」生成或更新。",
                    "请将 XCAGI / 扩展内 SQLite 连接指向 Mod 根下的相对路径，例如：",
                    f"  {sub_raw}/products.db",
                    "部署到 XCAGI/mods/<mod_id>/ 后，上述路径相对于该 Mod 文件夹。",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    # 去重保持顺序
    uniq: list[str] = []
    for r in planned:
        if r not in uniq:
            uniq.append(r)
    return uniq


def collect_sources_from_dir(dir_path: Path, glob_pat: str = "*.db") -> list[Path]:
    d = Path(dir_path).expanduser().resolve()
    if not d.is_dir():
        raise NotADirectoryError(f"不是目录: {d}")
    return sorted(p for p in d.glob(glob_pat) if p.is_file())
