"""
Template upload handler for Excel, Word, and logo images.
Provides file validation, storage, and metadata extraction.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import UploadFile
from PIL import Image

ALLOWED_EXTENSIONS = {
    "excel": {".xlsx", ".xlsm"},
    "word": {".docx"},
    "logo": {".png", ".jpg", ".jpeg", ".gif", ".svg"},
}

ALLOWED_MIME_TYPES = {
    "excel": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
    },
    "word": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    "logo": {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/svg+xml",
    },
}

MAX_FILE_SIZE = 10 * 1024 * 1024


def get_upload_dir() -> Path:
    """Get the upload directory path."""
    workspace_root = os.environ.get("WORKSPACE_ROOT", "").strip()
    if workspace_root and os.path.isdir(workspace_root):
        upload_dir = Path(workspace_root) / "uploads" / "templates"
    else:
        upload_dir = Path.cwd() / "uploads" / "templates"
    
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def validate_file_extension(filename: str, file_type: Literal["excel", "word", "logo"]) -> bool:
    """Validate file extension against allowed types."""
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS.get(file_type, set())


def validate_mime_type(content_type: str | None, file_type: Literal["excel", "word", "logo"]) -> bool:
    """Validate MIME type against allowed types."""
    if not content_type:
        return True
    return content_type in ALLOWED_MIME_TYPES.get(file_type, set())


async def validate_upload_file(
    file: UploadFile,
    file_type: Literal["excel", "word", "logo"],
    max_size: int = MAX_FILE_SIZE,
) -> tuple[bool, str | None]:
    """
    Validate uploaded file.
    
    Returns:
        (is_valid, error_message)
    """
    if not file.filename:
        return False, "文件名不能为空"
    
    if not validate_file_extension(file.filename, file_type):
        allowed = ", ".join(ALLOWED_EXTENSIONS.get(file_type, set()))
        return False, f"不支持的文件类型，允许：{allowed}"
    
    if file.content_type and not validate_mime_type(file.content_type, file_type):
        return False, f"文件 MIME 类型不匹配：{file.content_type}"
    
    content = await file.read()
    if len(content) > max_size:
        return False, f"文件大小超过限制 ({max_size // 1024 // 1024}MB)"
    
    file.file.seek(0)
    return True, None


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving the original extension."""
    suffix = Path(original_filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    return unique_name


def save_uploaded_file(file: UploadFile, subdirectory: str | None = None) -> tuple[Path, str]:
    """
    Save uploaded file to disk.
    
    Returns:
        (file_path, unique_filename)
    """
    upload_dir = get_upload_dir()
    
    if subdirectory:
        upload_dir = upload_dir / subdirectory
        upload_dir.mkdir(parents=True, exist_ok=True)
    
    unique_filename = generate_unique_filename(file.filename or "uploaded_file")
    file_path = upload_dir / unique_filename
    
    with open(file_path, "wb") as buffer:
        if file.file.tell() != 0:
            file.file.seek(0)
        buffer.write(file.file.read())
    
    return file_path, unique_filename


def generate_logo_thumbnail(file_path: Path, thumbnail_size: tuple[int, int] = (100, 100)) -> Path | None:
    """
    Generate thumbnail for logo image.
    
    Returns:
        thumbnail_path or None if generation failed
    """
    try:
        with Image.open(file_path) as img:
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            thumbnail_path = file_path.parent / f"{file_path.stem}_thumb{file_path.suffix}"
            img.save(thumbnail_path)
            return thumbnail_path
    except Exception:
        return None


def get_file_info(file_path: Path) -> dict[str, Any]:
    """Get basic file information."""
    stat = file_path.stat()
    return {
        "size": stat.st_size,
        "size_human": format_file_size(stat.st_size),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
    }


def format_file_size(size_bytes: int) -> str:
    """Format file size to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
