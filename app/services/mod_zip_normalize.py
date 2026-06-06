"""Mod 安装包 zip 布局规范化（与 ``mod_store._normalize_package_zip`` 语义一致）。"""

from __future__ import annotations

import os
import tempfile
import zipfile


def normalize_package_zip_path(src: str) -> str:
    """Return a zip path compatible with ModManager.extract_package.

    The legacy installer expects manifest.json at zip root. Public Catalog
    artifacts may instead be wrapped as mod-id/manifest.json, so flatten that
    single top-level folder into a temporary zip.
    """
    if not zipfile.is_zipfile(src):
        return src
    with zipfile.ZipFile(src, "r") as zf:
        names = [n for n in zf.namelist() if n and not n.endswith("/")]
        if "manifest.json" in names:
            return src
        top_levels = {
            n.split("/", 1)[0] for n in names if "/" in n and n.split("/", 1)[0] != "META-INF"
        }
        if len(top_levels) != 1:
            return src
        root_name = next(iter(top_levels))
        if f"{root_name}/manifest.json" not in names:
            return src
        fd, normalized = tempfile.mkstemp(prefix="xcagi-mod-flat-", suffix=".zip")
        os.close(fd)
        with zipfile.ZipFile(normalized, "w", zipfile.ZIP_DEFLATED) as out:
            for info in zf.infolist():
                if info.is_dir() or not info.filename.startswith(f"{root_name}/"):
                    continue
                arc = info.filename[len(root_name) + 1 :]
                if not arc:
                    continue
                out.writestr(arc, zf.read(info.filename))
        return normalized
