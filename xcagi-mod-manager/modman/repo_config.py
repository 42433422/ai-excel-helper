"""Web 仓库 UI 使用的本地路径配置（写入项目根 .modrepo-config.json）。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from modman.store import default_library, default_xcagi_root, project_root


CONFIG_NAME = ".modrepo-config.json"


@dataclass
class RepoConfig:
    library_root: str = ""
    xcagi_root: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RepoConfig":
        return cls(
            library_root=str(d.get("library_root") or "").strip(),
            xcagi_root=str(d.get("xcagi_root") or "").strip(),
        )


def config_path() -> Path:
    return project_root() / CONFIG_NAME


def load_config() -> RepoConfig:
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
