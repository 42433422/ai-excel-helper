from __future__ import annotations

import io
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from modman.manifest_util import (
    folder_name_must_match_id,
    read_manifest,
    save_manifest_validated,
    validate_manifest_dict,
    write_manifest,
)
from modman.repo_config import (
    RepoConfig,
    load_config,
    resolved_library,
    resolved_xcagi,
    resolved_xcagi_backend_url,
    save_config,
)
from modman.scaffold import create_mod
from modman.blueprint_scan import scan_flask_route_decorators
from modman.fhd_shell_export import write_fhd_shell_mods_json
from modman.surface_bundle import load_bundled_extension_surface
from modman.store import (
    deploy_to_xcagi,
    import_zip,
    iter_mod_dirs,
    list_mod_relative_files,
    list_mods,
    project_root,
    pull_from_xcagi,
    remove_mod,
)
from modstore_server.authoring import slim_openapi_paths
from modstore_server.constants import DEFAULT_API_PORT, DEFAULT_XCAGI_BACKEND_URL
from modstore_server.file_safe import read_text_file, resolve_under_mod, write_text_file

_TAGS = [
    {"name": "health", "description": "服务探活"},
    {"name": "config", "description": "库路径、XCAGI 根目录、后端 URL、导出 FHD 壳层 /api/mods JSON"},
    {"name": "mods", "description": "Mod 列表、详情、manifest、文件读写、导入导出"},
    {"name": "sync", "description": "与 XCAGI/mods 推送与拉回"},
    {"name": "debug", "description": "沙箱目录、primary 批量标记、XCAGI 状态代理"},
    {"name": "authoring", "description": "扩展面文档、蓝图路由静态扫描、宿主 OpenAPI 合并"},
]

app = FastAPI(
    title="MODstore",
    version="0.2.0",
    description=(
        "XCAGI Mod 本地库与调试辅助 API。"
        f"\n\n**交互式文档**：本页同源的 [`/docs`](./docs)（Swagger UI）、[`/redoc`](./redoc)。"
        f"\n**机器可读**：[`/openapi.json`](./openapi.json)。"
        f"\n\n默认假设 XCAGI HTTP 后端在 `{DEFAULT_XCAGI_BACKEND_URL}`（可在配置中覆盖）。"
        f"\n开发时 API 默认监听 `127.0.0.1:{DEFAULT_API_PORT}`。"
    ),
    openapi_tags=_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


STATE_FILENAME = "_modstore_state.json"


def _cfg() -> RepoConfig:
    return load_config()


def _lib() -> Path:
    p = resolved_library(_cfg())
    p.mkdir(parents=True, exist_ok=True)
    return p


def _state_path() -> Path:
    return _lib() / STATE_FILENAME


def _load_state() -> Dict[str, Any]:
    p = _state_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(updates: Dict[str, Any]) -> None:
    st = _load_state()
    st.update({k: v for k, v in updates.items() if v is not None})
    p = _state_path()
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ConfigDTO(BaseModel):
    library_root: str = ""
    xcagi_root: str = ""
    xcagi_backend_url: str = ""


class CreateModDTO(BaseModel):
    mod_id: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)


class SyncDTO(BaseModel):
    mod_ids: Optional[List[str]] = None


class ManifestPutDTO(BaseModel):
    manifest: Dict[str, Any]


class ModFilePutDTO(BaseModel):
    path: str = Field(..., min_length=1)
    content: str = ""


class SandboxDTO(BaseModel):
    mod_id: str = Field(..., min_length=1)
    mode: str = Field(default="copy", pattern="^(copy|symlink)$")


class FocusPrimaryDTO(BaseModel):
    mod_id: str = Field(..., min_length=1)


class ExportFhdShellDTO(BaseModel):
    """空字符串表示写入默认路径 ``<FHD>/backend/shell/fhd_shell_mods.json``。"""

    output_path: str = ""


def _fhd_repo_root() -> Path:
    """MODstore 位于 ``<FHD>/MODstore`` 时的上级目录。"""
    return Path(__file__).resolve().parent.parent.parent


def _assert_path_inside_fhd_repo(fhd: Path, target: Path) -> None:
    fhd_r = fhd.resolve()
    tgt_r = target.resolve()
    if not tgt_r.is_relative_to(fhd_r):
        raise HTTPException(400, "output_path 必须位于 FHD 仓库根目录内")


def _mod_dir(mod_id: str) -> Path:
    if not mod_id or "/" in mod_id or "\\" in mod_id:
        raise HTTPException(400, "非法 mod id")
    d = _lib() / mod_id
    if not d.is_dir():
        raise HTTPException(404, f"Mod 不存在: {mod_id}")
    return d


@app.get("/api/health", tags=["health"])
def health():
    return {"ok": True}


@app.get("/api/config", tags=["config"])
def get_config():
    cfg = _cfg()
    lib = resolved_library(cfg)
    xc = resolved_xcagi(cfg)
    st = _load_state()
    return {
        "library_root": str(lib),
        "xcagi_root": str(xc) if xc else "",
        "library_exists": lib.is_dir(),
        "xcagi_ok": bool(xc and (xc / "mods").is_dir()),
        "saved_library_root": cfg.library_root,
        "saved_xcagi_root": cfg.xcagi_root,
        "saved_xcagi_backend_url": cfg.xcagi_backend_url,
        "xcagi_backend_url": resolved_xcagi_backend_url(cfg),
        "state": {
            "last_sandbox_mods_root": st.get("last_sandbox_mods_root") or "",
            "last_sandbox_mod_id": st.get("last_sandbox_mod_id") or "",
            "focus_mod_id": st.get("focus_mod_id") or "",
        },
    }


@app.post("/api/export/fhd-shell-mods", tags=["config"])
def api_export_fhd_shell_mods(body: ExportFhdShellDTO = Body(default_factory=ExportFhdShellDTO)):
    """
    将当前库导出为 FHD ``GET /api/mods`` 使用的 JSON 文件（与 ``modman export-fhd-shell`` 相同数据）。
    ``output_path`` 留空则写入 ``<FHD>/backend/shell/fhd_shell_mods.json``。
    """
    fhd = _fhd_repo_root()
    if not fhd.is_dir():
        raise HTTPException(500, "无法定位 FHD 仓库根目录（预期 MODstore 位于 FHD/MODstore）")
    raw = body.output_path or ""
    raw = raw.strip()
    if raw:
        target = Path(raw).expanduser().resolve()
    else:
        target = (fhd / "backend" / "shell" / "fhd_shell_mods.json").resolve()
    _assert_path_inside_fhd_repo(fhd, target)
    lib = _lib()
    n = write_fhd_shell_mods_json(lib, target)
    return {"ok": True, "path": str(target), "count": n}


@app.put("/api/config", tags=["config"])
def put_config(body: ConfigDTO):
    lr = (body.library_root or "").strip()
    xr = (body.xcagi_root or "").strip()
    url = (body.xcagi_backend_url or "").strip()
    cfg = RepoConfig(
        library_root=str(Path(lr).expanduser().resolve()) if lr else "",
        xcagi_root=str(Path(xr).expanduser().resolve()) if xr else "",
        xcagi_backend_url=url,
    )
    save_config(cfg)
    if cfg.library_root:
        Path(cfg.library_root).mkdir(parents=True, exist_ok=True)
    return get_config()


@app.get("/api/mods", tags=["mods"])
def api_list_mods():
    rows = list_mods(_lib())
    return {"data": rows}


@app.get("/api/mods/{mod_id}", tags=["mods"])
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


@app.get("/api/authoring/extension-surface", tags=["authoring"])
def api_authoring_extension_surface(merge_host: bool = False):
    bundled = load_bundled_extension_surface()
    result: Dict[str, Any] = {
        "ok": True,
        "bundled": bundled,
        "host_openapi": None,
        "host_openapi_error": None,
    }
    if merge_host:
        cfg = _cfg()
        base = resolved_xcagi_backend_url(cfg).rstrip("/")
        url = f"{base}/openapi.json"
        try:
            with httpx.Client(timeout=20.0) as client:
                r = client.get(url)
            if r.status_code >= 400:
                result["host_openapi_error"] = f"HTTP {r.status_code} from {url}"
            else:
                spec = r.json()
                routes = slim_openapi_paths(spec if isinstance(spec, dict) else {})
                result["host_openapi"] = {
                    "base_url": base,
                    "openapi_url": url,
                    "route_count": len(routes),
                    "routes": routes,
                }
        except httpx.RequestError as e:
            result["host_openapi_error"] = f"{type(e).__name__}: {e} ({url})"
        except json.JSONDecodeError as e:
            result["host_openapi_error"] = f"openapi.json 非 JSON: {e}"
    return result


@app.get("/api/mods/{mod_id}/blueprint-routes", tags=["authoring"])
def api_mod_blueprint_routes(mod_id: str):
    d = _mod_dir(mod_id)
    for rel in ("backend/blueprints.py", "blueprints.py"):
        p = d / rel
        if p.is_file():
            routes = scan_flask_route_decorators(p)
            return {"ok": True, "file": rel, "routes": routes}
    return {
        "ok": True,
        "file": None,
        "routes": [],
        "hint": "未找到 backend/blueprints.py 或根目录 blueprints.py",
    }


@app.get("/api/mods/{mod_id}/authoring-summary", tags=["authoring"])
def api_mod_authoring_summary(mod_id: str):
    d = _mod_dir(mod_id)
    data, err = read_manifest(d)
    if err or not data:
        raise HTTPException(400, err or "manifest 无效")
    ve = validate_manifest_dict(data)
    fn = folder_name_must_match_id(d, data)
    if fn:
        ve = list(ve) + [fn]
    bp_file: str | None = None
    bp_routes: List[Dict[str, Any]] = []
    for rel in ("backend/blueprints.py", "blueprints.py"):
        p = d / rel
        if p.is_file():
            bp_file = rel
            bp_routes = scan_flask_route_decorators(p)
            break
    return {
        "ok": True,
        "id": mod_id,
        "manifest_backend": data.get("backend") if isinstance(data.get("backend"), dict) else {},
        "manifest_frontend": data.get("frontend") if isinstance(data.get("frontend"), dict) else {},
        "validation_ok": len(ve) == 0,
        "warnings": ve,
        "blueprint_file": bp_file,
        "blueprint_routes": bp_routes,
    }


@app.put("/api/mods/{mod_id}/manifest", tags=["mods"])
def api_put_manifest(mod_id: str, body: ManifestPutDTO):
    d = _mod_dir(mod_id)
    try:
        warnings = save_manifest_validated(d, body.manifest)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "warnings": warnings}


@app.get("/api/mods/{mod_id}/file", tags=["mods"])
def api_get_mod_file(mod_id: str, path: str):
    d = _mod_dir(mod_id)
    try:
        p = resolve_under_mod(d, path)
        text = read_text_file(p)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    return {"path": path.replace("\\", "/").lstrip("/"), "content": text}


@app.put("/api/mods/{mod_id}/file", tags=["mods"])
def api_put_mod_file(mod_id: str, body: ModFilePutDTO):
    d = _mod_dir(mod_id)
    try:
        p = resolve_under_mod(d, body.path)
        write_text_file(p, body.content)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    manifest_warnings: List[str] = []
    if p.name == "manifest.json" and p.parent.resolve() == d.resolve():
        data, err = read_manifest(d)
        if data and not err:
            manifest_warnings = validate_manifest_dict(data)
            fn = folder_name_must_match_id(d, data)
            if fn:
                manifest_warnings = list(manifest_warnings) + [fn]
    return {"ok": True, "manifest_warnings": manifest_warnings}


@app.post("/api/mods/create", tags=["mods"])
def api_create_mod(body: CreateModDTO):
    mid = body.mod_id.strip().lower().replace(" ", "-")
    try:
        dest = create_mod(mid, body.display_name.strip(), _lib())
    except FileExistsError as e:
        raise HTTPException(409, str(e)) from e
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "path": str(dest), "id": mid}


@app.delete("/api/mods/{mod_id}", tags=["mods"])
def api_delete_mod(mod_id: str):
    try:
        remove_mod(_lib(), mod_id)
    except FileNotFoundError:
        raise HTTPException(404, "不存在") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}


@app.post("/api/mods/import", tags=["mods"])
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


@app.get("/api/mods/{mod_id}/export", tags=["mods"])
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


@app.post("/api/sync/push", tags=["sync"])
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


@app.post("/api/sync/pull", tags=["sync"])
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


@app.post("/api/debug/sandbox", tags=["debug"])
def api_debug_sandbox(body: SandboxDTO):
    mod_id = body.mod_id.strip()
    _mod_dir(mod_id)
    lib = _lib()
    src = (lib / mod_id).resolve()
    root = project_root()
    sand = root / "debug_sandbox"
    sand.mkdir(parents=True, exist_ok=True)
    session = uuid.uuid4().hex[:12]
    mods_root = (sand / session / "mods").resolve()
    mods_root.mkdir(parents=True, exist_ok=True)
    dst = mods_root / mod_id
    if dst.exists():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    try:
        if body.mode == "symlink":
            try:
                os.symlink(src, dst, target_is_directory=True)
            except OSError:
                shutil.copytree(src, dst)
        else:
            shutil.copytree(src, dst)
    except OSError as e:
        raise HTTPException(500, f"创建沙箱失败: {e}") from e
    path_str = str(mods_root)
    _save_state(
        {
            "last_sandbox_mods_root": path_str,
            "last_sandbox_mod_id": mod_id,
            "last_sandbox_session": session,
        }
    )
    return {
        "ok": True,
        "session": session,
        "mods_root": path_str,
        "mod_id": mod_id,
        "xcagi_mods_root_env": f"XCAGI_MODS_ROOT={path_str}",
        "hint": "重启 XCAGI 后端后，仅会从此目录加载 Mod。",
    }


@app.post("/api/debug/focus-primary", tags=["debug"])
def api_debug_focus_primary(body: FocusPrimaryDTO):
    target = body.mod_id.strip()
    _mod_dir(target)
    lib = _lib()
    updated: List[str] = []
    for d in iter_mod_dirs(lib):
        data, err = read_manifest(d)
        if err or not data:
            continue
        mid = (data.get("id") or d.name).strip()
        data["primary"] = mid == target
        try:
            write_manifest(d, data)
            updated.append(mid)
        except OSError as e:
            raise HTTPException(500, f"写入失败 {d.name}: {e}") from e
    _save_state({"focus_mod_id": target})
    return {"ok": True, "primary_mod_id": target, "updated_manifests": updated}


@app.get("/api/fhd/db-tokens/status", tags=["debug"])
def api_fhd_db_tokens_status():
    """
    代理 FHD ``GET /api/fhd/db-tokens/status``：返回宿主进程是否已配置只读/写入 DB 令牌（无明文）。
    与「路径与同步」中的后端 URL 一致（可为 FHD http_app :8000）。
    """
    cfg = _cfg()
    base = resolved_xcagi_backend_url(cfg).rstrip("/")
    url = f"{base}/api/fhd/db-tokens/status"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url)
    except httpx.RequestError as e:
        return {
            "ok": False,
            "error": str(e),
            "url": url,
            "data": None,
        }
    try:
        payload = r.json()
    except json.JSONDecodeError:
        payload = {"raw": r.text[:2000]}
    ok = 200 <= r.status_code < 300
    return {
        "ok": ok,
        "status_code": r.status_code,
        "url": url,
        "data": payload if ok else None,
        "error": None if ok else (r.text or str(payload))[:500],
    }


@app.get("/api/xcagi/loading-status", tags=["debug"])
def api_xcagi_loading_status():
    cfg = _cfg()
    base = resolved_xcagi_backend_url(cfg)
    url = f"{base}/api/mods/loading-status"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url)
    except httpx.RequestError as e:
        return {
            "ok": False,
            "error": str(e),
            "url": url,
            "data": None,
        }
    try:
        payload = r.json()
    except json.JSONDecodeError:
        payload = {"raw": r.text[:2000]}
    ok = 200 <= r.status_code < 300
    return {
        "ok": ok,
        "status_code": r.status_code,
        "url": url,
        "data": payload,
    }


@app.get("/api/xcagi/installed-mods", tags=["sync"])
def api_xcagi_installed_mods():
    """
    扫描配置中的 XCAGI 根目录下 ``mods/``：与 ``push`` 部署目标一致，
    用于 MODstore 首页「当前接入」展示（磁盘上的扩展包，非实时进程内状态）。
    """
    cfg = _cfg()
    xc = resolved_xcagi(cfg)
    if not xc:
        return {
            "ok": False,
            "error": "未配置有效的 XCAGI 根目录（「路径与同步」或环境变量）",
            "mods_path": "",
            "mods": [],
            "primary_mod": None,
            "primary_mod_count": 0,
        }
    mods_dir = (xc / "mods").resolve()
    if not mods_dir.is_dir():
        return {
            "ok": True,
            "mods_path": str(mods_dir),
            "mods": [],
            "note": "XCAGI/mods 目录尚不存在",
            "primary_mod": None,
            "primary_mod_count": 0,
        }
    rows: List[Dict[str, Any]] = []
    for d in iter_mod_dirs(mods_dir):
        data, err = read_manifest(d)
        if err or not data:
            rows.append(
                {
                    "id": d.name,
                    "name": "",
                    "version": "",
                    "primary": False,
                    "ok": False,
                    "error": err or "manifest 无效",
                }
            )
            continue
        rows.append(
            {
                "id": str(data.get("id") or d.name).strip() or d.name,
                "name": str(data.get("name") or "").strip(),
                "version": str(data.get("version") or "").strip(),
                "primary": bool(data.get("primary")),
                "ok": True,
            }
        )
    rows.sort(key=lambda r: str(r.get("id") or ""))
    primary_rows = [r for r in rows if r.get("primary") and r.get("ok") is not False]
    primary_mod = primary_rows[0] if len(primary_rows) == 1 else None
    return {
        "ok": True,
        "mods_path": str(mods_dir),
        "mods": rows,
        "primary_mod": primary_mod,
        "primary_mod_count": len(primary_rows),
    }


def _maybe_mount_ui() -> None:
    root = Path(__file__).resolve().parent.parent
    dist = root / "web" / "dist"
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
