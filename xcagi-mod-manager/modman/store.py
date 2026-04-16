from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

from modman.manifest_util import (
    folder_name_must_match_id,
    read_manifest,
    validate_manifest_dict,
)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_library() -> Path:
    env = __import__("os").environ.get("MODMAN_LIBRARY", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (project_root() / "library").resolve()


def default_xcagi_root() -> Optional[Path]:
    import os

    for key in ("XCAGI_ROOT", "MODMAN_XCAGI_ROOT"):
        v = os.environ.get(key, "").strip()
        if v:
            p = Path(v).expanduser().resolve()
            if p.is_dir():
                return p
    sibling = project_root().parent / "XCAGI"
    if sibling.is_dir():
        return sibling.resolve()
    return None


def iter_mod_dirs(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "manifest.json").is_file():
            yield child


def list_mods(library: Path) -> List[dict]:
    rows: List[dict] = []
    for d in iter_mod_dirs(library):
        data, err = read_manifest(d)
        if err or not data:
            rows.append(
                {
                    "path": str(d),
                    "id": d.name,
                    "ok": False,
                    "error": err or "empty",
                }
            )
            continue
        ve = validate_manifest_dict(data)
        fn = folder_name_must_match_id(d, data)
        if fn:
            ve.append(fn)
        rows.append(
            {
                "path": str(d),
                "id": data.get("id", d.name),
                "name": data.get("name", ""),
                "version": data.get("version", ""),
                "primary": bool(data.get("primary")),
                "ok": len(ve) == 0,
                "warnings": ve,
            }
        )
    return rows


def _copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, dirs_exist_ok=False)


def ingest_mod(src: Path, library: Path) -> Path:
    src = src.resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"源不是目录: {src}")
    data, err = read_manifest(src)
    if err or not data:
        raise ValueError(err or "manifest 无效")
    ve = validate_manifest_dict(data)
    mid = (data.get("id") or "").strip()
    if not mid:
        raise ValueError("manifest 缺少 id")
    if ve:
        raise ValueError("manifest 校验未通过: " + "; ".join(ve))
    dest = library / mid
    library.mkdir(parents=True, exist_ok=True)
    _copytree(src, dest)
    return dest


def deploy_to_xcagi(
    mod_ids: Optional[List[str]],
    library: Path,
    xcagi_root: Path,
    *,
    replace: bool = True,
) -> List[str]:
    mods_dir = xcagi_root / "mods"
    if not mods_dir.is_dir():
        mods_dir.mkdir(parents=True, exist_ok=True)
    done: List[str] = []
    candidates = list_mods(library)
    id_set = set(mod_ids) if mod_ids else None
    for row in candidates:
        mid = row["id"]
        if id_set is not None and mid not in id_set:
            continue
        if not row.get("ok"):
            raise ValueError(f"Mod {mid} 校验未通过，跳过部署: {row.get('warnings')}")
        src = Path(row["path"])
        dst = mods_dir / mid
        if dst.exists():
            if not replace:
                raise FileExistsError(f"目标已存在: {dst}")
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        done.append(mid)
    return done


def pull_from_xcagi(
    mod_ids: Optional[List[str]],
    library: Path,
    xcagi_root: Path,
    *,
    replace: bool = True,
) -> List[str]:
    mods_dir = xcagi_root / "mods"
    if not mods_dir.is_dir():
        raise FileNotFoundError(f"XCAGI mods 目录不存在: {mods_dir}")
    done: List[str] = []
    for child in sorted(mods_dir.iterdir()):
        if not child.is_dir():
            continue
        if mod_ids and child.name not in mod_ids:
            continue
        if not (child / "manifest.json").is_file():
            continue
        dest = library / child.name
        library.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if not replace:
                raise FileExistsError(f"库中已存在: {dest}")
            shutil.rmtree(dest)
        shutil.copytree(child, dest)
        done.append(child.name)
    return done


def export_zip(mod_dir: Path, zip_path: Path) -> None:
    mod_dir = mod_dir.resolve()
    if not (mod_dir / "manifest.json").is_file():
        raise FileNotFoundError(f"不是有效 Mod 目录: {mod_dir}")
    zip_path = zip_path.resolve()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in mod_dir.rglob("*"):
            if f.is_file():
                arc = f.relative_to(mod_dir)
                zf.write(f, arc.as_posix())


def import_zip(zip_path: Path, library: Path, *, replace: bool = True) -> Path:
    zip_path = zip_path.resolve()
    library.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        if not names:
            raise ValueError("空 zip")
        top_levels = {n.split("/")[0].strip() for n in names if n.strip()}
        if len(top_levels) != 1:
            raise ValueError(
                "zip 顶层应只有一个文件夹（例如 my-mod/manifest.json），实际: "
                + ", ".join(sorted(top_levels)[:10])
            )
        root_name = next(iter(top_levels))
        extract_to = library / root_name
        if extract_to.exists():
            if not replace:
                raise FileExistsError(str(extract_to))
            shutil.rmtree(extract_to)
        zf.extractall(library)
    mod_dir = library / root_name
    data, err = read_manifest(mod_dir)
    if err or not data:
        shutil.rmtree(mod_dir, ignore_errors=True)
        raise ValueError(err or "解压后 manifest 无效")
    mid = (data.get("id") or "").strip()
    if mid != mod_dir.name:
        shutil.rmtree(mod_dir, ignore_errors=True)
        raise ValueError(
            f"zip 内文件夹名 {mod_dir.name!r} 须与 manifest.id {mid!r} 一致"
        )
    ve = validate_manifest_dict(data)
    if ve:
        raise ValueError("manifest: " + "; ".join(ve))
    return mod_dir


def write_registry_note(library: Path, note: dict) -> None:
    p = library / "_registry.json"
    p.write_text(json.dumps(note, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remove_mod(library: Path, mod_id: str) -> None:
    if not mod_id or "/" in mod_id or "\\" in mod_id or mod_id in (".", ".."):
        raise ValueError("非法 mod id")
    lib = library.resolve()
    p = (library / mod_id).resolve()
    if p.parent.resolve() != lib:
        raise ValueError("非法路径")
    if not p.is_dir():
        raise FileNotFoundError(mod_id)
    shutil.rmtree(p)


def list_mod_relative_files(mod_dir: Path, *, max_files: int = 400) -> List[str]:
    mod_dir = mod_dir.resolve()
    out: List[str] = []
    for f in sorted(mod_dir.rglob("*")):
        if not f.is_file():
            continue
        if any(part.startswith(".") for part in f.relative_to(mod_dir).parts):
            continue
        out.append(f.relative_to(mod_dir).as_posix())
        if len(out) >= max_files:
            break
    return out
