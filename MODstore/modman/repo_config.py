"""Web 仓库 UI 使用的本地路径配置（写入项目根 .modstore-config.json）。"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from modman.constants import DEFAULT_XCAGI_BACKEND_URL
from modman.store import default_library, default_xcagi_root, project_root

CONFIG_NAME = ".modstore-config.json"
LEGACY_CONFIG_NAME = ".modrepo-config.json"


@dataclass
class RepoConfig:
    library_root: str = ""
    xcagi_root: str = ""
    xcagi_backend_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RepoConfig":
        return cls(
            library_root=str(d.get("library_root") or "").strip(),
            xcagi_root=str(d.get("xcagi_root") or "").strip(),
            xcagi_backend_url=str(d.get("xcagi_backend_url") or "").strip(),
        )


def config_path() -> Path:
    return project_root() / CONFIG_NAME


def legacy_config_path() -> Path:
    return project_root() / LEGACY_CONFIG_NAME


def _migrate_legacy_if_needed() -> None:
    new_p = config_path()
    old_p = legacy_config_path()
    if new_p.is_file() or not old_p.is_file():
        return
    try:
        shutil.copy2(old_p, new_p)
    except OSError:
        pass


def load_config() -> RepoConfig:
    _migrate_legacy_if_needed()
    p = config_path()
    if not p.is_file():
        return RepoConfig()
    try:
        return RepoConfig.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError):
        return RepoConfig()


def save_config(cfg: RepoConfig) -> None:
    p = config_path()
    p.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolved_library(cfg: RepoConfig) -> Path:
    if cfg.library_root:
        return Path(cfg.library_root).expanduser().resolve()
    return default_library()


def resolved_xcagi(cfg: RepoConfig) -> Optional[Path]:
    if cfg.xcagi_root:
        p = Path(cfg.xcagi_root).expanduser().resolve()
        return p if p.is_dir() else None
    return default_xcagi_root()


def resolved_xcagi_backend_url(cfg: RepoConfig) -> str:
    u = (cfg.xcagi_backend_url or "").strip().rstrip("/")
    if u:
        return u
    return DEFAULT_XCAGI_BACKEND_URL
