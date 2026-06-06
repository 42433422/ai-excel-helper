"""Workspace 代码编辑 API（Brain / 规划工具）。"""

from __future__ import annotations

import difflib
import hashlib
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.domain.ai.tier import assert_p2_elevated_claim_or_raise, resolve_ai_tier

router = APIRouter(prefix="/api/code-editor", tags=["code-editor"])

_EDIT_STORE: dict[str, dict[str, Any]] = {}

_TEXT_EXT_OK = frozenset(
    {
        ".py",
        ".txt",
        ".md",
        ".vue",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".json",
        ".css",
        ".scss",
        ".html",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".cfg",
    }
)


def _workspace_root() -> Path:
    raw = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if not raw:
        raise HTTPException(status_code=500, detail="WORKSPACE_ROOT is not set")
    return Path(raw).resolve()


def _safe_rel_path(rel: str) -> Path:
    s = (rel or "").strip().replace("\\", "/")
    if not s or ".." in Path(s).parts:
        raise HTTPException(status_code=400, detail="invalid path")
    root = _workspace_root()
    target = (root / s).resolve()
    try:
        target.relative_to(root)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="path escapes workspace") from e
    return target


def chat_completion_no_tools(messages: list, **kw: object) -> str:
    """由 LLM 层实现；测试中 mock 此符号。"""
    raise NotImplementedError("chat_completion_no_tools not configured")


def _unified_diff(old: str, new: str, path: str) -> str:
    lines = list(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
    return "".join(lines)


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


@router.get("/status")
def code_editor_status() -> dict:
    return {
        "success": True,
        "phase": "edit_diff_apply",
        "capabilities": ["analyze_readonly", "apply_p2", "propose_new_file", "draft_p2"],
        "version": 4,
    }


class AnalyzeBody(BaseModel):
    path: str | None = None
    message: str | None = None


@router.post("/analyze")
def code_editor_analyze(body: AnalyzeBody) -> dict:
    if not (body.path and str(body.path).strip()):
        return {"success": True, "kind": "noop"}
    rel = str(body.path).strip()
    try:
        path = _safe_rel_path(rel)
    except HTTPException:
        raise
    if not path.is_file():
        return {"success": True, "kind": "noop"}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {"success": True, "kind": "text_preview", "preview": text}


class EditBody(BaseModel):
    path: str
    new_content: str
    create_if_missing: bool = False


@router.post("/edit")
def code_editor_edit(body: EditBody) -> dict:
    rel = str(body.path or "").strip()
    path = _safe_rel_path(rel)
    create = bool(body.create_if_missing)
    is_new = False
    old = ""
    if path.is_file():
        old = path.read_text(encoding="utf-8", errors="replace")
    elif path.is_dir():
        raise HTTPException(status_code=404, detail="path is a directory")
    elif create:
        ext = path.suffix.lower()
        if ext not in _TEXT_EXT_OK:
            raise HTTPException(
                status_code=400, detail="extension not allowed for create_if_missing"
            )
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        old = ""
        is_new = True
    else:
        raise HTTPException(status_code=404, detail="file not found")

    new = body.new_content
    edit_id = f"edit_{uuid.uuid4().hex}"
    diff = _unified_diff(old, new, rel)
    _EDIT_STORE[edit_id] = {
        "path": str(path),
        "rel": rel,
        "old": old,
        "new": new,
        "unified_diff": diff,
        "is_new_file": is_new,
        "old_sha256": _sha256_text(old),
    }
    return {
        "success": True,
        "edit_id": edit_id,
        "unified_diff": diff,
        "is_new_file": is_new,
    }


@router.get("/diff/{edit_id}")
def code_editor_diff(edit_id: str) -> dict:
    row = _EDIT_STORE.get(edit_id)
    if not row:
        raise HTTPException(status_code=404, detail="unknown edit_id")
    return {"success": True, "unified_diff": row.get("unified_diff") or ""}


@router.post("/apply/{edit_id}")
def code_editor_apply(edit_id: str, request: Request) -> dict:
    if resolve_ai_tier(request) != "p2":
        raise HTTPException(status_code=403, detail="p2 required")
    assert_p2_elevated_claim_or_raise(request)

    row = _EDIT_STORE.get(edit_id)
    if not row:
        raise HTTPException(status_code=404, detail="unknown edit_id")

    path = Path(row["path"])
    old_disk = ""
    if path.is_file():
        old_disk = path.read_text(encoding="utf-8", errors="replace")
    elif not row.get("is_new_file"):
        raise HTTPException(status_code=404, detail="file missing")

    if row.get("is_new_file"):
        if path.exists():
            raise HTTPException(status_code=409, detail="file already exists")
        path.write_text(row["new"], encoding="utf-8")
        del _EDIT_STORE[edit_id]
        return {"success": True, "created": True}

    if _sha256_text(old_disk) != row["old_sha256"]:
        raise HTTPException(status_code=409, detail="file changed on disk")

    path.write_text(row["new"], encoding="utf-8")
    del _EDIT_STORE[edit_id]
    return {"success": True, "created": False}


class DraftBody(BaseModel):
    path: str
    instruction: str


@router.post("/draft")
def code_editor_draft(request: Request, body: DraftBody) -> dict:
    if resolve_ai_tier(request) != "p2":
        raise HTTPException(status_code=403, detail="p2 required")
    assert_p2_elevated_claim_or_raise(request)

    rel = str(body.path or "").strip()
    path = _safe_rel_path(rel)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    current = path.read_text(encoding="utf-8", errors="replace")
    messages = [
        {"role": "system", "content": "Return only the full new file content."},
        {
            "role": "user",
            "content": f"File {rel}:\n```\n{current}\n```\nInstruction: {body.instruction}",
        },
    ]
    try:
        out = chat_completion_no_tools(messages)
    except Exception as e:
        return {"success": False, "message": str(e), "is_new_file": False}

    if isinstance(out, str) and out.strip().upper().startswith("ERROR:"):
        return {"success": False, "message": out.strip(), "is_new_file": False}

    return {"success": True, "proposed_new_content": out, "is_new_file": False}
