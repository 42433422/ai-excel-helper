"""本机用户头像存储（桌面/开发环境 userData/uploads/avatars）。"""

from __future__ import annotations

import os
from pathlib import Path

from app.utils.path_utils import get_upload_dir

AVATAR_API_PATH = "/api/auth/avatar"
ALLOWED_AVATAR_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "gif", "webp"})
MAX_AVATAR_BYTES = 4 * 1024 * 1024


def avatar_storage_dir() -> Path:
    path = Path(get_upload_dir()) / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


def avatar_file_for_user(user_id: int) -> Path | None:
    if not user_id:
        return None
    folder = avatar_storage_dir()
    for ext in ALLOWED_AVATAR_EXTENSIONS:
        candidate = folder / f"{user_id}.{ext}"
        if candidate.is_file():
            return candidate
    return None


def media_type_for_path(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "application/octet-stream")


def public_avatar_url(stored: str | None) -> str:
    text = str(stored or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text.startswith(AVATAR_API_PATH):
        return text
    return AVATAR_API_PATH


def save_user_avatar_file(user_id: int, content: bytes, ext: str) -> Path:
    normalized = (ext or "png").lower().lstrip(".")
    if normalized not in ALLOWED_AVATAR_EXTENSIONS:
        raise ValueError(f"不支持的图片格式：{ext}")
    if len(content) > MAX_AVATAR_BYTES:
        raise ValueError("头像文件不能超过 4MB")
    folder = avatar_storage_dir()
    for old in folder.glob(f"{user_id}.*"):
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass
    target = folder / f"{user_id}.{normalized}"
    target.write_bytes(content)
    return target
