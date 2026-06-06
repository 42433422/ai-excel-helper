"""File logging for packaged desktop runs (userData/logs)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_HANDLER_MARK = "xcagi_desktop_rotating_file"


def attach_desktop_file_logging(
    log_dir: str | Path, *, max_bytes: int = 10_485_760, backup_count: int = 5
) -> None:
    """Append a rotating file handler to the root logger (desktop only).

    Idempotent: safe if ``create_fastapi_app`` is invoked more than once (e.g. tests).
    """

    root = logging.getLogger()
    if any(getattr(h, "_xcagi_handler_mark", None) == _HANDLER_MARK for h in root.handlers):
        return

    log_path = Path(log_dir).expanduser().resolve()
    log_path.mkdir(parents=True, exist_ok=True)
    file_path = log_path / "xcagi.log"

    fh = RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    setattr(fh, "_xcagi_handler_mark", _HANDLER_MARK)
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    logging.getLogger(__name__).info("Desktop file logging enabled: %s", file_path)
