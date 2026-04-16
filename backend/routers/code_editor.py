"""
代码编辑器 / Agent 编排 API。

- analyze：只读预览（不调 LLM）。
- edit：在 WORKSPACE_ROOT 内对 UTF-8 文本文件生成修改提案，返回 edit_id 并缓存 unified diff。
- diff/{id}：取回缓存的 unified diff。
- apply/{id}：校验 P2（X-XCAGI-AI-Tier + X-XCAGI-Elevated-Token）后写入 new_content；若磁盘文件在提案后已被改动则 409。
- POST /edit 可选 `create_if_missing: true`：path 尚不存在时在已有父目录下按「新建 UTF-8 文本」提案（old 视为空）；apply 时若路径已被占用则 409。
- POST /draft：仅 P2；单次无工具 LLM 调用，根据当前文件与 instruction 生成 proposed_new_content（不落盘）。
"""

from __future__ import annotations

import difflib
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from fastapi import APIRouter, Body, HTTPException, Request

from backend.ai_tier import assert_p2_elevated_claim_or_raise, resolve_ai_tier
from backend.planner import chat_completion_no_tools
from backend.workspace import resolve_safe_workspace_relpath, workspace_root

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/code-editor", tags=["code-editor"])

_MAX_READ_BYTES: Final[int] = 96 * 1024
_MAX_PREVIEW_CHARS: Final[int] = 12_000
_MAX_NEW_CONTENT_BYTES: Final[int] = 96 * 1024
_PROPOSAL_TTL_SEC: Final[int] = 3600
_MAX_PROPOSALS: Final[int] = 200
_DEFAULT_DRAFT_CONTEXT_CHARS: Final[int] = 48_000
_MAX_INSTRUCTION_CHARS: Final[int] = 8000

_DRAFT_SYSTEM: Final[str] = (
    "你是工作区内的代码编辑助手。用户会给出相对路径、当前文件全文（或新建空文件）和修改说明。\n"
    "你必须只输出修改后的完整文件正文：不要使用 markdown 代码围栏；不要在正文前后添加任何解释或标题。\n"
    "若无法满足要求，只输出一行：ERROR: <简短原因>（必须以 ERROR: 开头）。"
)

_TEXT_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".py",
        ".pyi",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".env",
        ".sql",
        ".sh",
        ".bat",
        ".ps1",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".vue",
        ".css",
        ".scss",
        ".less",
        ".html",
        ".htm",
        ".xml",
        ".csv",
        ".rs",
        ".go",
        ".java",
        ".kt",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".dockerfile",
    }
)

_SPREADSHEET_SUFFIXES: Final[frozenset[str]] = frozenset({".xlsx", ".xls", ".xlsm"})

_SPECIAL_TEXT_NAMES: Final[frozenset[str]] = frozenset(
    {"dockerfile", "makefile", "gemfile", "rakefile", "jenkinsfile"}
)

_proposals_lock = threading.Lock()
_proposals: dict[str, "_Proposal"] = {}


@dataclass
class _Proposal:
    path_rel: str
    old_content: str
    new_content: str
    unified_diff: str
    created_mono: float
    is_new_file: bool = False


def _looks_like_utf8_text(chunk: bytes) -> bool:
    if not chunk:
        return True
    if b"\x00" in chunk[:8192]:
        return False
    try:
        chunk[:8192].decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _gc_proposals_unlocked(now: float) -> None:
    dead = [k for k, v in _proposals.items() if now - v.created_mono > _PROPOSAL_TTL_SEC]
    for k in dead:
        del _proposals[k]
    while len(_proposals) > _MAX_PROPOSALS:
        oldest = min(_proposals.items(), key=lambda kv: kv[1].created_mono)[0]
        del _proposals[oldest]


def _read_workspace_utf8_text_strict(path_rel: str) -> tuple[Path, str]:
    """与 analyze 相同的范围/类型约束，但要求整文件为合法 UTF-8（用于可逆写入）。"""
    target = resolve_safe_workspace_relpath(path_rel)
    if not target.exists():
        raise HTTPException(status_code=404, detail="path not found")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="path is a directory")

    suffix = target.suffix.lower()
    name_lower = target.name.lower()
    eff_suffix = suffix
    if not eff_suffix and name_lower == "dockerfile":
        eff_suffix = ".dockerfile"

    stat = target.stat()
    size = stat.st_size

    if eff_suffix in _SPREADSHEET_SUFFIXES:
        raise HTTPException(status_code=400, detail="binary spreadsheet cannot be edited here")

    if size > _MAX_READ_BYTES:
        raise HTTPException(status_code=400, detail="file too large for edit")

    raw = target.read_bytes()
    head = raw[:8192]
    treat_as_text = eff_suffix in _TEXT_SUFFIXES or name_lower in _SPECIAL_TEXT_NAMES
    if not treat_as_text and not _looks_like_utf8_text(head):
        raise HTTPException(status_code=400, detail="file does not look like UTF-8 text")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="file is not valid UTF-8") from e
    return target, text


def _validate_new_file_candidate(target: Path) -> None:
    """path 不存在：要求父目录已存在，且为可识别的文本文件名。"""
    if target.exists():
        raise HTTPException(status_code=400, detail="path already exists")
    parent = target.parent
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(
            status_code=400,
            detail="parent directory does not exist under workspace",
        )

    suffix = target.suffix.lower()
    name_lower = target.name.lower()
    eff_suffix = suffix
    if not eff_suffix and name_lower == "dockerfile":
        eff_suffix = ".dockerfile"

    if eff_suffix in _SPREADSHEET_SUFFIXES:
        raise HTTPException(status_code=400, detail="binary spreadsheet path not allowed for text create")

    if eff_suffix not in _TEXT_SUFFIXES and name_lower not in _SPECIAL_TEXT_NAMES:
        raise HTTPException(
            status_code=400,
            detail="new_file requires a recognized text extension (or Dockerfile/Makefile/Gemfile/...)",
        )


def _old_state_for_edit(path_rel: str, *, create_if_missing: bool) -> tuple[Path, str, bool]:
    """
    返回 (resolved_target, old_utf8_text, is_new_file)。
    is_new_file 为 True 时 old 固定为 ""，仅当 create_if_missing 且 path 不存在时成立。
    """
    target = resolve_safe_workspace_relpath(path_rel)
    if target.is_dir():
        raise HTTPException(status_code=400, detail="path is a directory")

    if target.exists():
        _, text = _read_workspace_utf8_text_strict(path_rel)
        return target, text, False

    if not create_if_missing:
        raise HTTPException(
            status_code=404,
            detail="path not found; set create_if_missing=true to create a new UTF-8 text file under an existing directory",
        )

    _validate_new_file_candidate(target)
    return target, "", True


def _draft_context_max_chars() -> int:
    raw = (os.environ.get("FHD_CODE_EDITOR_DRAFT_CONTEXT_CHARS") or "").strip()
    if not raw:
        return _DEFAULT_DRAFT_CONTEXT_CHARS
    try:
        n = int(raw)
    except ValueError:
        return _DEFAULT_DRAFT_CONTEXT_CHARS
    return max(4000, min(n, 90_000))


def _strip_outer_fenced_block(text: str) -> str:
    """去掉水平空白与可选外层 ``` 围栏；不剥掉正文末尾换行（便于源码文件）。"""
    t = text.strip("\r\t \u00a0")
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if len(lines) < 2:
        return t
    for i in range(1, len(lines)):
        if lines[i].strip() == "```":
            return "\n".join(lines[1:i]).strip("\r\t \u00a0")
    return "\n".join(lines[1:]).strip("\r\t \u00a0")


def _require_p2_for_apply(request: Request) -> None:
    assert_p2_elevated_claim_or_raise(request)
    if resolve_ai_tier(request) != "p2":
        raise HTTPException(
            status_code=403,
            detail="apply requires P2: set X-XCAGI-AI-Tier: p2 and X-XCAGI-Elevated-Token to match server FHD_AI_ELEVATED_TOKEN",
        )


def _preview_text_bytes(raw: bytes) -> tuple[str, bool]:
    text = raw.decode("utf-8", errors="replace")
    truncated = len(text) > _MAX_PREVIEW_CHARS
    return text[:_MAX_PREVIEW_CHARS], truncated


@router.get("/status")
def code_editor_status() -> dict[str, Any]:
    """健康与能力说明。"""
    root = str(workspace_root())
    return {
        "success": True,
        "phase": "edit_diff_apply",
        "version": 4,
        "capabilities": [
            "status",
            "analyze_readonly",
            "draft_p2",
            "propose_edit",
            "propose_new_file",
            "fetch_diff",
            "apply_p2",
        ],
        "workspace_root": root,
        "message": "POST /draft 需 P2+模型密钥，按 instruction 生成正文；edit/diff/apply 流程不变。",
    }


@router.post("/analyze")
def code_editor_analyze(body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """只读：校验 path 位于工作区，返回文件信息与文本预览（不写入、不调模型）。"""
    message = body.get("message")
    message_echo = (str(message) if message is not None else "")[:500]
    path_rel = (body.get("path") or "").strip()
    if not path_rel:
        return {
            "success": True,
            "kind": "noop",
            "message": "提供 body.path（相对 WORKSPACE_ROOT）以进行只读预览；可选 message 仅回显。",
            "message_echo": message_echo,
        }

    target = resolve_safe_workspace_relpath(path_rel)
    if not target.exists():
        raise HTTPException(status_code=404, detail="path not found")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="path is a directory")

    suffix = target.suffix.lower()
    name_lower = target.name.lower()
    eff_suffix = suffix
    if not eff_suffix and name_lower == "dockerfile":
        eff_suffix = ".dockerfile"

    stat = target.stat()
    size = stat.st_size

    if eff_suffix in _SPREADSHEET_SUFFIXES:
        return {
            "success": True,
            "kind": "binary_spreadsheet",
            "path": path_rel,
            "size_bytes": size,
            "message": "二进制表格；请在对话中使用 Excel 相关工具分析。",
            "message_echo": message_echo,
        }

    if size > _MAX_READ_BYTES:
        return {
            "success": True,
            "kind": "file_too_large",
            "path": path_rel,
            "size_bytes": size,
            "max_read_bytes": _MAX_READ_BYTES,
            "message": "文件超过只读预览大小上限，未读取内容。",
            "message_echo": message_echo,
        }

    raw = target.read_bytes()
    head = raw[:8192]
    treat_as_text = eff_suffix in _TEXT_SUFFIXES or name_lower in _SPECIAL_TEXT_NAMES
    if not treat_as_text and not _looks_like_utf8_text(head):
        return {
            "success": True,
            "kind": "binary_sniff",
            "path": path_rel,
            "size_bytes": size,
            "message": "非文本后缀且内容不似 UTF-8 文本，未做预览。",
            "message_echo": message_echo,
        }

    preview, preview_truncated = _preview_text_bytes(raw)
    return {
        "success": True,
        "kind": "text_preview",
        "path": path_rel,
        "size_bytes": size,
        "preview": preview,
        "preview_truncated": preview_truncated,
        "message_echo": message_echo,
    }


@router.post("/draft")
def code_editor_draft(request: Request, body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """
    P2 + 已配置 LLM：根据 instruction 生成 proposed_new_content（不写入磁盘、不注册 edit_id）。
    """
    _require_p2_for_apply(request)

    instruction = (body.get("instruction") or "").strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="instruction is required")
    if len(instruction) > _MAX_INSTRUCTION_CHARS:
        raise HTTPException(status_code=400, detail="instruction too long")

    path_rel = (body.get("path") or "").strip()
    if not path_rel:
        raise HTTPException(status_code=400, detail="path is required")

    create_if_missing = body.get("create_if_missing") is True
    _, old_content, is_new_file = _old_state_for_edit(path_rel, create_if_missing=create_if_missing)

    cap = _draft_context_max_chars()
    truncated = len(old_content) > cap
    old_for_prompt = old_content[:cap] if truncated else old_content

    user_msg = (
        f"相对路径: {path_rel}\n"
        f"是否新建空文件: {is_new_file}\n"
        f"当前文件内容{'（已截断）' if truncated else ''}:\n{old_for_prompt}\n\n"
        f"修改说明:\n{instruction}"
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _DRAFT_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = chat_completion_no_tools(messages, strip_response=False)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception:
        logger.exception("code_editor draft: LLM call failed")
        raise HTTPException(status_code=502, detail="draft LLM call failed") from None

    raw_check = (raw or "").strip()
    if raw_check[:6].upper() == "ERROR:":
        return {
            "success": False,
            "path": path_rel,
            "is_new_file": is_new_file,
            "message": raw_check,
            "proposed_new_content": None,
        }

    proposed = _strip_outer_fenced_block(raw or "")
    if len(proposed.encode("utf-8")) > _MAX_NEW_CONTENT_BYTES:
        return {
            "success": False,
            "path": path_rel,
            "is_new_file": is_new_file,
            "message": "model output exceeds new_content size limit",
            "proposed_new_content": None,
        }

    return {
        "success": True,
        "path": path_rel,
        "is_new_file": is_new_file,
        "context_truncated": truncated,
        "proposed_new_content": proposed,
    }


@router.post("/edit")
def code_editor_edit(body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """
    根据 path 与 new_content 生成 unified diff 并缓存。
    不要求 P2（提案可公开生成）；落盘见 POST /apply。
    """
    path_rel = (body.get("path") or "").strip()
    if not path_rel:
        raise HTTPException(status_code=400, detail="path is required")
    raw_new = body.get("new_content")
    if not isinstance(raw_new, str):
        raise HTTPException(status_code=400, detail="new_content must be a string")
    new_content = raw_new
    if len(new_content.encode("utf-8")) > _MAX_NEW_CONTENT_BYTES:
        raise HTTPException(status_code=400, detail="new_content too large")

    create_if_missing = body.get("create_if_missing") is True
    _, old_content, is_new_file = _old_state_for_edit(path_rel, create_if_missing=create_if_missing)

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    unified = "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path_rel}",
            tofile=f"b/{path_rel}",
            lineterm="\n",
        )
    )

    edit_id = secrets.token_hex(16)
    now = time.monotonic()
    prop = _Proposal(
        path_rel=path_rel,
        old_content=old_content,
        new_content=new_content,
        unified_diff=unified or f"# no textual changes for {path_rel}\n",
        created_mono=now,
        is_new_file=is_new_file,
    )
    with _proposals_lock:
        _gc_proposals_unlocked(now)
        _proposals[edit_id] = prop

    return {
        "success": True,
        "edit_id": edit_id,
        "path": path_rel,
        "is_new_file": is_new_file,
        "unified_diff": prop.unified_diff,
        "old_bytes": len(old_content.encode("utf-8")),
        "new_bytes": len(new_content.encode("utf-8")),
    }


@router.get("/diff/{diff_id}")
def code_editor_diff(diff_id: str) -> dict[str, Any]:
    with _proposals_lock:
        _gc_proposals_unlocked(time.monotonic())
        prop = _proposals.get(diff_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="unknown or expired edit_id")
    return {
        "success": True,
        "edit_id": diff_id,
        "path": prop.path_rel,
        "is_new_file": prop.is_new_file,
        "unified_diff": prop.unified_diff,
    }


@router.post("/apply/{apply_id}")
def code_editor_apply(apply_id: str, request: Request, body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """
    P2 专属：将缓存的 new_content 写入 path（须与提案生成时磁盘内容一致）。
    """
    _ = body
    _require_p2_for_apply(request)

    with _proposals_lock:
        _gc_proposals_unlocked(time.monotonic())
        prop = _proposals.pop(apply_id, None)
    if prop is None:
        raise HTTPException(status_code=404, detail="unknown or expired edit_id")

    target = resolve_safe_workspace_relpath(prop.path_rel)

    if prop.is_new_file:
        if target.exists():
            with _proposals_lock:
                _proposals[apply_id] = prop
            raise HTTPException(
                status_code=409,
                detail="path already exists; cannot apply new_file proposal",
            )
        if not target.parent.is_dir():
            with _proposals_lock:
                _proposals[apply_id] = prop
            raise HTTPException(status_code=409, detail="parent directory missing; refresh proposal")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(prop.new_content, encoding="utf-8", newline="\n")
        return {
            "success": True,
            "path": prop.path_rel,
            "written_bytes": len(prop.new_content.encode("utf-8")),
            "created": True,
        }

    _, current = _read_workspace_utf8_text_strict(prop.path_rel)
    if current != prop.old_content:
        with _proposals_lock:
            _proposals[apply_id] = prop
        raise HTTPException(
            status_code=409,
            detail="file changed since proposal was created; create a new edit proposal",
        )

    target.write_text(prop.new_content, encoding="utf-8", newline="\n")
    return {
        "success": True,
        "path": prop.path_rel,
        "written_bytes": len(prop.new_content.encode("utf-8")),
        "created": False,
    }
