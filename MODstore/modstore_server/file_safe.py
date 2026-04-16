"""Mod 目录内文本文件的受限读写。"""

from __future__ import annotations

from pathlib import Path

ALLOWED_SUFFIXES = frozenset(
    {
        ".py",
        ".json",
        ".vue",
        ".ts",
        ".js",
        ".mjs",
        ".cjs",
        ".css",
        ".md",
        ".txt",
        ".html",
    }
)
MAX_FILE_BYTES = 512 * 1024


def normalize_rel_path(raw: str) -> str:
    s = (raw or "").strip().replace("\\", "/").lstrip("/")
    if not s or ".." in s.split("/"):
        raise ValueError("非法路径")
    return s


def resolve_under_mod(mod_dir: Path, rel: str) -> Path:
    mod_dir = mod_dir.resolve()
    rel = normalize_rel_path(rel)
    candidate = (mod_dir / rel).resolve()
    try:
        candidate.relative_to(mod_dir)
    except ValueError as e:
        raise ValueError("路径越界") from e
    suf = candidate.suffix.lower()
    if suf not in ALLOWED_SUFFIXES:
        raise ValueError(f"不允许的扩展名（允许: {', '.join(sorted(ALLOWED_SUFFIXES))}）")
    return candidate


def read_text_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError("不是文件或不存在")
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError(f"文件过大（>{MAX_FILE_BYTES} 字节）")
    return path.read_text(encoding="utf-8", errors="strict")


def write_text_file(path: Path, content: str) -> None:
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError(f"内容过大（>{MAX_FILE_BYTES} 字节）")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
