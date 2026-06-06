from __future__ import annotations

import os
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.desktop_runtime import (
    ensure_desktop_dirs,
    is_desktop_mode,
    load_or_create_profile,
    redact_database_url,
    resolve_storage_mode,
)
from app.desktop_runtime.model_downloader import ModelAsset, download_model, load_manifest
from app.desktop_runtime.support_bundle import build_support_bundle_zip

router = APIRouter(prefix="/api/desktop", tags=["desktop-runtime"])


class DownloadModelRequest(BaseModel):
    name: str
    version: str
    url: str
    sha256: str
    size: int | None = None


@router.get("/status")
def desktop_status(request: Request):
    dirs = ensure_desktop_dirs(os.environ.get("XCAGI_DATA_DIR"))
    db_url = os.environ.get("DATABASE_URL", "")
    prof_path, profile = load_or_create_profile(dirs["root"])
    storage_mode = resolve_storage_mode(db_url, profile)
    app = request.app
    mods_full = bool(getattr(app.state, "mods_full_load_done", False))
    mods_bg = bool(getattr(app.state, "mods_background_load_scheduled", False))
    timing: dict = {}
    try:
        from app.fastapi_app.startup_timing import startup_timing_snapshot

        timing = startup_timing_snapshot()
    except Exception:
        timing = {}
    return {
        "desktopMode": is_desktop_mode(),
        "dataDir": str(dirs["root"]),
        "database": str(dirs["data"] / "xcagi.db"),
        "modsDir": str(dirs["mods"]),
        "modelsDir": str(dirs["models"]),
        "webModeCompatible": True,
        "storageMode": storage_mode,
        "databaseUrlRedacted": redact_database_url(db_url),
        "profilePath": str(prof_path),
        "modsRoutesLoaded": bool(getattr(app.state, "mods_routes_loaded", False)),
        "modsFullLoadDone": mods_full,
        "modsBackgroundLoadScheduled": mods_bg,
        "readyForUi": True,
        "modsReady": mods_full or not mods_bg,
        "startupTiming": timing,
    }


@router.get("/models")
def list_models():
    dirs = ensure_desktop_dirs(os.environ.get("XCAGI_DATA_DIR"))
    root = dirs["models"]
    models = []
    for path in root.glob("*/*"):
        if path.is_dir():
            models.append({"name": path.parent.name, "version": path.name, "path": str(path)})
    return {"models": models}


@router.post("/models/download")
def download_model_asset(request: DownloadModelRequest):
    if not is_desktop_mode():
        raise HTTPException(status_code=409, detail="模型下载仅在桌面模式下可写入 userData")
    asset = ModelAsset(**request.model_dump())
    target = download_model(asset, data_dir=os.environ.get("XCAGI_DATA_DIR"))
    return {"ok": True, "path": str(target)}


@router.post("/models/install-manifest")
def install_manifest(path: str):
    if not is_desktop_mode():
        raise HTTPException(status_code=409, detail="模型下载仅在桌面模式下可写入 userData")
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="manifest not found")
    targets = [
        str(target)
        for target in (
            download_model(asset, data_dir=os.environ.get("XCAGI_DATA_DIR"))
            for asset in load_manifest(manifest_path)
        )
    ]
    return {"ok": True, "files": targets}


@router.get("/support-bundle")
def download_support_bundle(request: Request):
    """ZIP：环境摘要 + 近期后端日志节选（不含数据库正文）。仅桌面模式。"""
    if not is_desktop_mode():
        raise HTTPException(status_code=409, detail="诊断包仅在桌面模式下可用")
    try:
        raw = build_support_bundle_zip(fastapi_version=getattr(request.app, "version", "unknown"))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    buf = BytesIO(raw)
    buf.seek(0)
    fname = f"xcagi-support-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
