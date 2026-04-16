"""
代码编辑器 / Agent 编排 API。

analyze：只读，在工作区内解析 path 并返回元数据与文本预览（不调用 LLM）。
edit / diff / apply：仍为规划项。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from fastapi import APIRouter, Body, HTTPException

from backend.workspace import resolve_safe_workspace_relpath, workspace_root

router = APIRouter(prefix="/api/code-editor", tags=["code-editor"])

_MAX_READ_BYTES: Final[int] = 96 * 1024
_MAX_PREVIEW_CHARS: Final[int] = 12_000

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


@router.get("/status")
def code_editor_status() -> dict[str, Any]:
    """健康与能力说明。"""
    root = str(workspace_root())
    return {
        "success": True,
        "phase": "readonly_analyze",
        "version": 1,
        "capabilities": ["status", "analyze_readonly"],
        "workspace_root": root,
        "message": "POST /analyze 可在 WORKSPACE_ROOT 下做只读文本预览；编辑/应用仍为规划项。",
    }


def _preview_text_bytes(raw: bytes) -> tuple[str, bool]:
    text = raw.decode("utf-8", errors="replace")
    truncated = len(text) > _MAX_PREVIEW_CHARS
    return text[:_MAX_PREVIEW_CHARS], truncated


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


@router.post("/edit")
def code_editor_edit(body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    _ = body
    return {
        "success": False,
        "placeholder": True,
        "message": "尚未实现：将返回结构化编辑建议或 patch。",
    }


@router.get("/diff/{diff_id}")
def code_editor_diff(diff_id: str) -> dict[str, Any]:
    _ = diff_id
    return {
        "success": False,
        "placeholder": True,
        "message": "尚未实现：将返回 unified diff 或结构化 diff。",
    }


@router.post("/apply/{apply_id}")
def code_editor_apply(apply_id: str, body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    _ = (apply_id, body)
    return {
        "success": False,
        "placeholder": True,
        "message": "尚未实现：将在校验 P2 与工作区后应用补丁。",
    }
