"""上传 API（继承自归档 upload 蓝图的端点契约）。"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.utils.secure_filename import secure_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "uploads",
    "temp",
)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _ensure_upload_folder() -> None:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/temp")
async def upload_temp(file: UploadFile | None = File(default=None)):
    try:
        _ensure_upload_folder()
        if file is None:
            return JSONResponse({"success": False, "message": "没有上传文件"}, status_code=400)
        if not file.filename:
            return JSONResponse({"success": False, "message": "文件名为空"}, status_code=400)
        if not _allowed_file(file.filename):
            return JSONResponse(
                {
                    "success": False,
                    "message": f"不支持的文件类型，仅支持：{', '.join(ALLOWED_EXTENSIONS)}",
                },
                status_code=400,
            )

        original_filename = secure_filename(file.filename) or "uploaded_file"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "png"
        new_filename = f"{timestamp}_{unique_id}.{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)

        content = await file.read()
        if len(content) > MAX_CONTENT_LENGTH:
            return JSONResponse({"success": False, "message": "文件过大"}, status_code=400)

        with open(file_path, "wb") as f:
            f.write(content)

        if not os.path.exists(file_path):
            logger.error("文件保存失败：%s", file_path)
            return JSONResponse({"success": False, "message": "文件保存失败"}, status_code=500)

        relative_path = os.path.join("uploads", "temp", new_filename)
        logger.info("文件上传成功：%s", relative_path)
        return JSONResponse(
            {
                "success": True,
                "file_path": relative_path,
                "filename": original_filename,
                "url": f"/{relative_path.replace(os.sep, '/')}",
                "size": os.path.getsize(file_path),
            }
        )
    except Exception as e:
        logger.error("文件上传失败：%s", e, exc_info=True)
        return JSONResponse({"success": False, "message": f"上传失败：{str(e)}"}, status_code=500)


@router.delete("/temp/{filename}")
def delete_temp_file(filename: str):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            return JSONResponse({"success": False, "message": "文件不存在"}, status_code=404)
        os.remove(file_path)
        return JSONResponse({"success": True, "message": "文件已删除"})
    except Exception as e:
        logger.error("删除文件失败：%s", e)
        return JSONResponse({"success": False, "message": f"删除失败：{str(e)}"}, status_code=500)


@router.get("/config")
def get_upload_config():
    return JSONResponse(
        {
            "success": True,
            "config": {
                "max_size": "16MB",
                "max_size_bytes": MAX_CONTENT_LENGTH,
                "allowed_extensions": list(ALLOWED_EXTENSIONS),
            },
        }
    )
