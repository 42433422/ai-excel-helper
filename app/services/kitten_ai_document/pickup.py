"""Short-lived storage for generated documents (pickup by opaque token).

默认写入本机磁盘目录（WORKSPACE_ROOT 或系统临时目录），多 worker / 热重载下
仍可与生成文档时的进程共享，避免仅内存 dict 导致的「链接无效或已过期」。
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_TTL_SEC = 86400
_MAX_ITEMS = 200

_CACHED_BASE: Path | None = None


def _sanitize_token(raw: str) -> str | None:
    t = (raw or "").strip()
    if not t or len(t) > 128:
        return None
    allowed = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if not all(c in allowed for c in t):
        return None
    return t


def _pickup_base_dir() -> Path:
    global _CACHED_BASE
    if _CACHED_BASE is not None:
        return _CACHED_BASE

    candidates: list[Path] = []
    env_dir = (os.environ.get("KITTEN_PICKUP_DIR") or "").strip()
    if env_dir:
        candidates.append(Path(env_dir))
    wr = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if wr:
        candidates.append(Path(wr) / ".runtime" / "kitten_document_pickup")
    candidates.append(Path(tempfile.gettempdir()) / "xcagi_kitten_document_pickup")

    last_err: Exception | None = None
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".write_probe"
            probe.write_text("1", encoding="utf-8")
            probe.unlink(missing_ok=True)
            _CACHED_BASE = p
            if p == candidates[-1] and wr and not env_dir:
                logger.info("kitten document pickup dir (fallback temp): %s", p)
            return p
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"kitten pickup: no writable directory ({last_err!r})")


def _prune_disk(base: Path) -> None:
    now = time.time()
    try:
        entries: list[tuple[float, Path]] = []
        for child in base.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            meta_path = child / "meta.json"
            try:
                ts = float(json.loads(meta_path.read_text(encoding="utf-8")).get("ts", 0))
            except Exception:
                ts = 0.0
            if now - ts > _TTL_SEC:
                shutil.rmtree(child, ignore_errors=True)
                continue
            entries.append((ts, child))

        overflow = len(entries) - _MAX_ITEMS
        if overflow > 0:
            entries.sort(key=lambda x: x[0])
            for _, path in entries[:overflow]:
                shutil.rmtree(path, ignore_errors=True)
    except Exception:
        logger.debug("kitten pickup prune skipped", exc_info=True)


def store_document_pickup(content: bytes, file_name: str, mime: str) -> str:
    base = _pickup_base_dir()
    for _ in range(8):
        tok = secrets.token_urlsafe(18)
        dest = base / tok
        try:
            dest.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            continue
        try:
            meta = {"ts": time.time(), "file_name": file_name, "mime": mime}
            (dest / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            (dest / "data.bin").write_bytes(content)
            with _LOCK:
                _prune_disk(base)
            return tok
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise
    raise RuntimeError("kitten pickup: token collision after retries")


def pop_document_pickup(token: str) -> tuple[bytes, str, str] | None:
    key = _sanitize_token(token)
    if not key:
        return None

    base = _pickup_base_dir()
    src = base / key
    work = base / f".consume.{key}.{uuid.uuid4().hex}"

    try:
        src.rename(work)
    except OSError:
        return None

    try:
        meta = json.loads((work / "meta.json").read_text(encoding="utf-8"))
        content = (work / "data.bin").read_bytes()
        ts = float(meta.get("ts", 0))
        if time.time() - ts > _TTL_SEC:
            return None
        fname = str(meta.get("file_name") or "download.bin")
        mime = str(meta.get("mime") or "application/octet-stream")
        return content, fname, mime
    except Exception:
        logger.debug("kitten pickup read failed for token prefix=%s", key[:6], exc_info=True)
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)
        with _LOCK:
            _prune_disk(base)
