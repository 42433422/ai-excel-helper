"""Shared upload helpers for FastAPI routes."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import UploadFile

from app.utils.path_utils import get_upload_dir
from app.utils.secure_filename import secure_filename


async def save_upload_file(upload: UploadFile, *, subdir: str) -> str:
    """
    Persist an uploaded file under ``get_upload_dir()/subdir``.

    Returns the absolute path to the saved file.
    """
    if not upload.filename:
        raise ValueError("上传文件缺少文件名")
    filename = secure_filename(upload.filename)
    upload_dir = os.path.join(get_upload_dir(), subdir)
    os.makedirs(upload_dir, exist_ok=True)
    resolved_path = os.path.join(upload_dir, filename)
    body = await upload.read()
    with open(resolved_path, "wb") as f:
        f.write(body)
    return resolved_path


def save_upload_bytes(content: bytes, *, subdir: str, filename: str) -> str:
    """Persist raw bytes to the upload directory."""
    safe_name = secure_filename(filename)
    upload_dir = Path(get_upload_dir()) / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = upload_dir / safe_name
    resolved_path.write_bytes(content)
    return str(resolved_path)
