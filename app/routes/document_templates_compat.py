"""
调用 ``app.services.document_templates_service`` 中的模板 API 实现（纯 Python，
不依赖 werkzeug）。

Phase 2C: 本模块由 ``app.routes.archive_templates_compat`` 更名而来,
``archive_templates_legacy`` 同步更名为 ``document_templates_service``,
文件内行为不变,仅名字脱离 "archive_" 前缀。

历史：本文件原先为过渡期提供「FastAPI 层 ↔ werkzeug 风格响应」的拆包器，
并用 werkzeug ``FileStorage`` 把 bytes 喂给 legacy 分析器。werkzeug 剥离后：

- 响应拆包走 **鸭子类型**（只要对象有 ``get_json()`` 就行），不再 ``isinstance``
  werkzeug 的 Response。``app.http.json_response`` 返回的 Starlette Response
  子类保留了该方法。
- ``FileStorage`` 替换为同目录的 ``_UploadLikeFile`` 轻量类，只实现
  ``filename`` / ``save(path)`` 两个模板分析器用到的点。
"""

from __future__ import annotations

import shutil
from io import BytesIO
from typing import Any, BinaryIO

from app.application.facades.template_facade import document_templates_service as _tpl


class _UploadLikeFile:
    """最小化的上传文件封装，仅实现 ``filename`` 与 ``save(path)``。

    旨在替换历史上的 ``werkzeug.datastructures.FileStorage``，给
    ``document_templates_service.analyze_template_with_upload`` 使用。
    """

    def __init__(
        self, stream: BinaryIO, filename: str, content_type: str = "application/octet-stream"
    ) -> None:
        self.stream = stream
        self.filename = filename
        self.content_type = content_type

    def save(self, dst: str) -> None:
        self.stream.seek(0)
        with open(dst, "wb") as fp:
            shutil.copyfileobj(self.stream, fp)


def _unpack_response(raw: Any) -> tuple[dict, int]:
    if isinstance(raw, tuple):
        resp = raw[0]
        code = int(raw[1]) if len(raw) > 1 else 200
    else:
        resp = raw
        code = int(getattr(resp, "status_code", 200) or 200)

    # 鸭子类型：app.http.json_response 返回的 Response 子类暴露了 get_json。
    get_json = getattr(resp, "get_json", None)
    if callable(get_json):
        data = get_json(silent=True)
        if isinstance(data, dict):
            return data, code
    return {"success": False, "message": "invalid templates response"}, 500


def run_archive_template_create(payload: dict | None) -> tuple[dict, int]:
    return _unpack_response(_tpl.create_template_with_payload(payload or {}))


def run_archive_template_update(payload: dict | None) -> tuple[dict, int]:
    return _unpack_response(_tpl.update_template_with_payload(payload or {}))


def run_archive_template_analyze(
    *,
    file_body: bytes,
    filename: str,
    template_name: str = "",
    template_scope: str = "",
) -> tuple[dict, int]:
    fs = _UploadLikeFile(
        stream=BytesIO(file_body),
        filename=filename,
        content_type="application/octet-stream",
    )
    return _unpack_response(_tpl.analyze_template_with_upload(fs, template_name, template_scope))
