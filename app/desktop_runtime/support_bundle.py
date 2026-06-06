"""Build a ZIP support bundle for customer diagnostics (desktop mode only)."""

from __future__ import annotations

import io
import json
import os
import platform
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from app.desktop_runtime.migrate import export_config

from .paths import ensure_desktop_dirs, is_desktop_mode


def _tail_bytes(path: Path, max_bytes: int = 2_097_152) -> bytes | None:
    if not path.is_file():
        return None
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size <= max_bytes:
                return f.read()
            f.seek(max(0, size - max_bytes))
            return f.read()
    except OSError:
        return None


def build_support_bundle_zip(
    *,
    data_dir: str | os.PathLike[str] | None = None,
    fastapi_version: str = "unknown",
) -> bytes:
    """Return ZIP bytes with non-secret diagnostics (no live DB copy)."""

    if not is_desktop_mode():
        raise RuntimeError("support bundle is only available in desktop mode")

    dirs = ensure_desktop_dirs(data_dir or os.environ.get("XCAGI_DATA_DIR"))
    root = dirs["root"]
    logs_dir = dirs["logs"]
    backups_dir = dirs["backups"]

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "generatedAtUtc": stamp,
        "fastapiAppVersion": fastapi_version,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "desktopPaths": export_config(data_dir),
        "backupFiles": sorted(p.name for p in backups_dir.glob("*.db") if p.is_file())[-50:],
        "note": "不含数据库正文；数据库备份请在 backups/ 目录单独拷贝。",
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "README.txt",
            (
                "XCAGI 诊断包\n"
                "------------\n"
                "将此 ZIP 提供给技术支持即可。\n"
                "- manifest.json：环境与路径摘要（不含密钥）。\n"
                "- xcagi.log（若存在）：后端近期日志节选。\n"
                "数据库文件默认不在包内；如需一并分析请单独发送 backups 下的 .db 备份。\n"
            ).encode("utf-8"),
        )
        zf.writestr(
            "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        )

        for name in ("xcagi.log", "xcagi.log.1", "xcagi.log.2"):
            chunk = _tail_bytes(logs_dir / name)
            if chunk:
                zf.writestr(f"logs/{name}", chunk)

    buf.seek(0)
    return buf.getvalue()
