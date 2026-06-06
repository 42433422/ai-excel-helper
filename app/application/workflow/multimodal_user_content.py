"""将 ``runtime_context["multimodal_attachments"]`` 转为 OpenAI 兼容的 user ``content``。

前端上传图片 / PDF 后，在 ``context`` 中附带 ``multimodal_attachments``（见字段说明）。
无附件时返回纯字符串，与历史行为一致；有附件时返回 ``content`` 数组（text + image_url）。
"""

from __future__ import annotations

import base64
import binascii
import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_MAX_ATTACHMENTS = 8
_MAX_B64_DECODE_BYTES = 14 * 1024 * 1024  # 单附件解码上限（约 14MB）
_MAX_PDF_TEXT_CHARS = 24_000
_MAX_PDF_PAGES = 10

_ALLOWED_IMAGE_MIME = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
_ALLOWED_PDF_MIME = frozenset({"application/pdf"})


def _normalize_mime(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s == "image/jpg":
        return "image/jpeg"
    return s


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    """解析 ``data:<mime>;base64,<payload>``，返回 (bytes, mime)。"""
    u = (data_url or "").strip()
    m = re.match(r"^data:([^;]+);base64,(.+)$", u, re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError("invalid data URL (expected data:<mime>;base64,...)")
    mime = _normalize_mime(m.group(1))
    b64 = m.group(2).strip()
    raw_bytes = base64.standard_b64decode(b64 + "=" * (-len(b64) % 4))
    if len(raw_bytes) > _MAX_B64_DECODE_BYTES:
        raise ValueError("attachment too large after decode")
    return raw_bytes, mime


def _maybe_downscale_image_jpeg(raw: bytes, mime: str) -> tuple[str, str]:
    """过大图片压成 JPEG data URL，降低 token / 限流风险。失败则回退原图 base64 data URL。"""
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except Exception:
        b64 = base64.standard_b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}", mime

    try:
        im = Image.open(io.BytesIO(raw))
        im = im.convert("RGB")
        im.thumbnail((2048, 2048))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85, optimize=True)
        out = buf.getvalue()
        b64 = base64.standard_b64encode(out).decode("ascii")
        return f"data:image/jpeg;base64,{b64}", "image/jpeg"
    except Exception as exc:
        logger.debug("image downscale skipped: %s", exc)
        b64 = base64.standard_b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}", mime


def _pdf_bytes_to_text(raw: bytes, filename: str) -> str:
    try:
        import pdfplumber  # type: ignore[import-not-found]
    except Exception as exc:
        return f"[PDF {filename}: 无法读取（缺少 pdfplumber: {exc}）]"

    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            chunks: list[str] = []
            for i, page in enumerate(pdf.pages[:_MAX_PDF_PAGES]):
                t = page.extract_text() or ""
                if t.strip():
                    chunks.append(f"--- page {i + 1} ---\n{t.strip()}")
            body = "\n\n".join(chunks).strip()
            if not body:
                return f"[PDF {filename}: 未解析到文本（可能是扫描件）]"
            if len(body) > _MAX_PDF_TEXT_CHARS:
                body = body[:_MAX_PDF_TEXT_CHARS] + "\n…(truncated)"
            return f"[PDF 文件: {filename}]\n{body}"
    except Exception as exc:
        logger.info("pdf extract failed name=%r: %s", filename, exc)
        return f"[PDF {filename}: 解析失败 {exc}]"


def build_openai_user_content(
    user_message: str,
    runtime_context: dict[str, Any] | None,
) -> str | list[dict[str, Any]]:
    """返回 ``str``（无附件）或 ``list``（多模态，OpenAI chat.completions 格式）。"""
    msg = (user_message or "").strip()
    if not runtime_context or not isinstance(runtime_context, dict):
        return msg

    raw_list = runtime_context.get("multimodal_attachments")
    if not isinstance(raw_list, list) or not raw_list:
        return msg

    parts: list[dict[str, Any]] = []
    if msg:
        parts.append({"type": "text", "text": msg})

    for item in raw_list[:_MAX_ATTACHMENTS]:
        if not isinstance(item, dict):
            continue
        filename = (
            str(item.get("filename") or item.get("name") or "attachment").strip() or "attachment"
        )
        mime_in = _normalize_mime(str(item.get("mime_type") or item.get("mime") or ""))
        data_url = str(item.get("data_url") or "").strip()
        b64_field = str(item.get("data_base64") or "").strip()
        kind = str(item.get("kind") or "").strip().lower()

        raw_bytes: bytes
        mime: str
        try:
            if data_url.startswith("data:"):
                raw_bytes, mime = _decode_data_url(data_url)
            elif b64_field:
                raw_bytes = base64.standard_b64decode(b64_field + "=" * (-len(b64_field) % 4))
                mime = mime_in or "application/octet-stream"
                if len(raw_bytes) > _MAX_B64_DECODE_BYTES:
                    raise ValueError("attachment too large")
            else:
                parts.append(
                    {
                        "type": "text",
                        "text": f"\n[跳过附件 {filename}: 无 data_url / data_base64]\n",
                    }
                )
                continue
        except (binascii.Error, ValueError, TypeError) as exc:
            parts.append({"type": "text", "text": f"\n[跳过附件 {filename}: {exc}]\n"})
            continue

        if mime_in and mime == "application/octet-stream":
            mime = mime_in

        if kind == "pdf" or mime in _ALLOWED_PDF_MIME:
            parts.append({"type": "text", "text": "\n" + _pdf_bytes_to_text(raw_bytes, filename)})
            continue

        if mime not in _ALLOWED_IMAGE_MIME:
            parts.append(
                {
                    "type": "text",
                    "text": f"\n[跳过不支持的附件类型 {filename}: mime={mime or 'unknown'}]\n",
                }
            )
            continue

        url, out_mime = _maybe_downscale_image_jpeg(raw_bytes, mime)
        parts.append({"type": "image_url", "image_url": {"url": url, "detail": "auto"}})
        if out_mime != mime:
            logger.debug("image re-encoded %s -> %s (%s)", mime, out_mime, filename)

    if not parts:
        return msg
    if len(parts) == 1 and parts[0].get("type") == "text":
        return str(parts[0].get("text") or msg)
    return parts


__all__ = ["build_openai_user_content"]
