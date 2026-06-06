"""沙盒专用最小 Mod 安装接口。

完整 ``app.fastapi_routes.mod_store_routes`` 会牵入部分重型依赖；线上沙盒只需要
市场的「推送并测试」能把 .xcmod 装进沙盒 mods 根目录。
"""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from sandbox_app.sandbox_settings import default_mods_root

router = APIRouter(prefix="/api/mod-store", tags=["sandbox-mod-store"])


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    root = dest.resolve()
    for info in zf.infolist():
        target = (dest / info.filename).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"Unsafe zip path: {info.filename}")
    zf.extractall(dest)


def _find_manifest_root(tmp_dir: Path) -> Path:
    direct = tmp_dir / "manifest.json"
    if direct.is_file():
        return tmp_dir
    candidates = list(tmp_dir.glob("*/manifest.json"))
    if len(candidates) == 1:
        return candidates[0].parent
    raise ValueError("未找到 manifest.json，或包内存在多个 manifest.json")


@router.post("/install")
async def install_mod(file: UploadFile = File(...)):
    mods_root = default_mods_root()
    mods_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="xcagi-sandbox-mod-") as td:
        tmp_dir = Path(td)
        zip_path = tmp_dir / (file.filename or "upload.xcmod")
        with zip_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

        extract_dir = tmp_dir / "extract"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path) as zf:
            _safe_extract(zf, extract_dir)

        manifest_root = _find_manifest_root(extract_dir)
        manifest = json.loads((manifest_root / "manifest.json").read_text(encoding="utf-8"))
        mod_id = str(manifest.get("id") or "").strip()
        if not mod_id:
            return JSONResponse(
                {"success": False, "message": "manifest.json 缺少 id", "sandbox": True},
                status_code=400,
            )

        target = mods_root / mod_id
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(manifest_root, target)

    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        mm = get_mod_manager()
        mm._refresh_mods_root_if_needed()
        mm.load_all_mods()
    except Exception as exc:
        return {
            "success": True,
            "message": f"Mod {mod_id} 已安装，但重新加载时有警告: {exc}",
            "data": {"id": mod_id, "path": str(target), "reload_warning": str(exc)},
            "sandbox": True,
        }

    return {
        "success": True,
        "message": f"Mod {mod_id} 已安装到沙盒",
        "data": {"id": mod_id, "path": str(target)},
        "sandbox": True,
    }
