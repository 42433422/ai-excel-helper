"""FHD 内嵌 MODstore：本地库状态、路径与 DTO（供 ``fhd_routes_*`` 使用）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from modman.repo_config import RepoConfig, load_config, resolved_library, resolved_xcagi

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
    portal_plans_url: str = ""
    portal_wallet_sync_url: str = ""


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


class EmployeeSandboxRunDTO(BaseModel):
    probe_http: bool = False


class SandboxDTO(BaseModel):
    mod_id: str = Field(..., min_length=1)
    mode: str = Field(default="copy", pattern="^(copy|symlink)$")


class FocusPrimaryDTO(BaseModel):
    mod_id: str = Field(..., min_length=1)


class FetchPortalWalletSecretDTO(BaseModel):
    sync_url: str = ""
    authorization: str = Field(..., min_length=8, description="如 Bearer <token> 或裸 token")


class ExportFhdShellDTO(BaseModel):
    output_path: str = ""


def _fhd_repo_root() -> Path:
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
