"""工作区与传统模式目录路径（供 FastAPI 路由与下载接口复用）。"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote

from fastapi import HTTPException


def workspace_root() -> Path:
    return Path(os.environ.get("WORKSPACE_ROOT", os.getcwd())).resolve()


def traditional_workspace_root() -> Path:
    base = workspace_root()
    tw = base / "traditional_workspace"
    tw.mkdir(parents=True, exist_ok=True)
    return tw


def traditional_resolve_path(rel: str) -> Path:
    """XCAGI 传统模式：在 WORKSPACE_ROOT/traditional_workspace 下解析相对路径。"""
    base = traditional_workspace_root()
    raw = unquote(rel or "").strip().replace("\\", "/").lstrip("/")
    target = (base / raw).resolve() if raw else base
    try:
        target.relative_to(base)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid path") from e
    return target


def resolve_safe_workspace_relpath(rel: str) -> Path:
    """在 WORKSPACE_ROOT 下解析相对路径；禁止 .. 与越出根目录。"""
    root = workspace_root()
    raw = unquote((rel or "").strip()).replace("\\", "/").lstrip("/")
    if not raw:
        raise HTTPException(status_code=400, detail="path required")
    if ".." in Path(raw).parts:
        raise HTTPException(status_code=400, detail="path must not contain '..'")
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="path outside workspace") from e
    return candidate
