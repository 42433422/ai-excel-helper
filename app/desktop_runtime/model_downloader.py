"""Model download manifest and file downloader for desktop deployments."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .paths import ensure_desktop_dirs

ProgressCallback = Callable[[str, int, int], None]


@dataclass(frozen=True)
class ModelAsset:
    name: str
    version: str
    url: str
    sha256: str
    size: int | None = None


def models_dir(data_dir: str | os.PathLike[str] | None = None) -> Path:
    return ensure_desktop_dirs(data_dir)["models"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: str | os.PathLike[str]) -> list[ModelAsset]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    assets = raw.get("models", raw)
    return [ModelAsset(**item) for item in assets]


def download_model(
    asset: ModelAsset,
    *,
    data_dir: str | os.PathLike[str] | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    target_dir = models_dir(data_dir) / asset.name / asset.version
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / Path(asset.url).name
    partial = target.with_suffix(target.suffix + ".part")

    if target.exists() and _sha256(target).lower() == asset.sha256.lower():
        return target

    request = urllib.request.Request(asset.url, headers={"User-Agent": "XCAGI-Desktop/7"})
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as out:
        total = asset.size or int(response.headers.get("Content-Length") or 0)
        copied = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            copied += len(chunk)
            if progress:
                progress(asset.name, copied, total)

    digest = _sha256(partial)
    if digest.lower() != asset.sha256.lower():
        partial.unlink(missing_ok=True)
        raise ValueError(f"模型 {asset.name} 校验失败: {digest}")

    shutil.move(str(partial), target)
    return target


def ensure_models(
    assets: Iterable[ModelAsset], *, data_dir: str | os.PathLike[str] | None = None
) -> list[Path]:
    return [download_model(asset, data_dir=data_dir) for asset in assets]
