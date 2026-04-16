from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from modman.manifest_util import (
    folder_name_must_match_id,
    read_manifest,
    save_manifest_validated,
    validate_manifest_dict,
)
from modman.repo_config import RepoConfig, load_config, resolved_library, resolved_xcagi, save_config
from modman.scaffold import create_mod
from modman.store import (
    deploy_to_xcagi,
    export_zip,
    import_zip,
    list_mod_relative_files,
    list_mods,
    pull_from_xcagi,
    remove_mod,
)

app = FastAPI(title="XCAGI Mod Repo", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cfg() -> RepoConfig:
    return load_config()


def _lib() -> Path:
    p = resolved_library(_cfg())
    p.mkdir(parents=True, exist_ok=True)
    return p


class ConfigDTO(BaseModel):
    library_root: str = ""
    xcagi_root: str = ""


class CreateModDTO(BaseModel):
    mod_id: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)


class SyncDTO(BaseModel):
    mod_ids: Optional[List[str]] = None


class ManifestPutDTO(BaseModel):
    manifest: Dict[str, Any]


def _mod_dir(mod_id: str) -> Path:
    if not mod_id or "/" in mod_id or "\\" in mod_id:
        raise HTTPException(400, "非法 mod id")
    d = _lib() / mod_id
    if not d.is_dir():
        raise HTTPException(404, f"Mod 不存在: {mod_id}")
    return d


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def get_config():
    cfg = _cfg()
    lib = resolved_library(cfg)
    xc = resolved_xcagi(cfg)
    return {
        "library_root": str(lib),
        "xcagi_root": str(xc) if xc else "",
        "library_exists": lib.is_dir(),
        "xcagi_ok": bool(xc and (xc / "mods").is_dir()),
        "saved_library_root": cfg.library_root,
        "saved_xcagi_root": cfg.xcagi_root,
    }


@app.put("/api/config")
def put_config(body: ConfigDTO):
    lr = (body.library_root or "").strip()
    xr = (body.xcagi_root or "").strip()
    cfg = RepoConfig(
        library_root=str(Path(lr).expanduser().resolve()) if lr else "",
        xcagi_root=str(Path(xr).expanduser().resolve()) if xr else "",
    )
    save_config(cfg)
    if cfg.library_root:
        Path(cfg.library_root).mkdir(parents=True, exist_ok=True)
    return get_config()


@app.get("/api/mods")
def api_list_mods():
    rows = list_mods(_lib())
    return {"data": rows}


@app.get("/api/mods/{mod_id}")
def api_get_mod(mod_id: str):
    d = _mod_dir(mod_id)
    data, err = read_manifest(d)
    if err or not data:
        raise HTTPException(400, err or "manifest 无效")
    ve = validate_manifest_dict(data)
    fn = folder_name_must_match_id(d, data)
    if fn:
        ve = list(ve) + [fn]
    files = list_mod_relative_files(d)
    return {
        "id": mod_id,
        "manifest": data,
        "validation_ok": len(ve) == 0,
        "warnings": ve,
        "files": files,
    }


@app.put("/api/mods/{mod_id}/manifest")
def api_put_manifest(mod_id: str, body: ManifestPutDTO):
    d = _mod_dir(mod_id)
    try:
        warnings = save_manifest_validated(d, body.manifest)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "warnings": warnings}


@app.post("/api/mods/create")
def api_create_mod(body: CreateModDTO):
    mid = body.mod_id.strip().lower().replace(" ", "-")
    try:
        dest = create_mod(mid, body.display_name.strip(), _lib())
    except FileExistsError as e:
        raise HTTPException(409, str(e)) from e
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "path": str(dest), "id": mid}


@app.delete("/api/mods/{mod_id}")
def api_delete_mod(mod_id: str):
    try:
        remove_mod(_lib(), mod_id)
    except FileNotFoundError:
        raise HTTPException(404, "不存在") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}


@app.post("/api/mods/import")
async def api_import_mod(file: UploadFile = File(...), replace: bool = True):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "请上传 .zip")
    raw = await file.read()
    if len(raw) > 80 * 1024 * 1024:
        raise HTTPException(400, "文件过大（>80MB）")
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    try:
        dest = import_zip(tmp_path, _lib(), replace=replace)
    except (ValueError, FileExistsError) as e:
        raise HTTPException(400, str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"ok": True, "id": dest.name, "path": str(dest)}


@app.get("/api/mods/{mod_id}/export")
def api_export_mod(mod_id: str):
    d = _mod_dir(mod_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in d.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(d).as_posix())
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{mod_id}.zip"'},
    )


@app.post("/api/sync/push")
def api_sync_push(body: SyncDTO):
    cfg = _cfg()
    xc = resolved_xcagi(cfg)
    if not xc:
        raise HTTPException(400, "未配置有效的 XCAGI 根目录（设置页）")
    lib = _lib()
    try:
        done = deploy_to_xcagi(body.mod_ids, lib, xc, replace=True)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "deployed": done}


@app.post("/api/sync/pull")
def api_sync_pull(body: SyncDTO):
    cfg = _cfg()
    xc = resolved_xcagi(cfg)
    if not xc:
        raise HTTPException(400, "未配置有效的 XCAGI 根目录")
    lib = _lib()
    try:
        done = pull_from_xcagi(body.mod_ids, lib, xc, replace=True)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e)) from e
    except FileExistsError as e:
        raise HTTPException(409, str(e)) from e
    return {"ok": True, "pulled": done}


def _maybe_mount_ui() -> None:
    """若已执行 npm run build，可由同一端口 8765 提供 UI（否则开发期用 Vite 5173）。"""
    root = Path(__file__).resolve().parent.parent
    dist = root / "modrepo-ui" / "dist"
    if not dist.is_dir():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="ui-assets")

    index_file = dist / "index.html"

    @app.get("/")
    def ui_root():
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(404)

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if (
            full_path.startswith("api")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path == "openapi.json"
        ):
            raise HTTPException(404)
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(404)


_maybe_mount_ui()
