"""
可持久化的 LAN 安全运行时配置（页面内改、立即生效）。

设计要点：
- 存成 ``<repo>/data/lan_settings.json``，和 ``lan_license.db`` 同目录，便于备份迁移。
- 覆写四个关键项：``enabled``、``license_secret``、``admin_bootstrap_key``、``allowed_cidrs``。
- ``get_lan_config()`` 读取 env 之后再叠加这里的覆写，所以 ``.env`` 仍然有效，
  但"页面保存"拥有更高优先级，避免用户改完 env 又改 UI 造成混淆。
- 写入时原子替换（写临时文件再 rename），避免多进程下读到半截。
- 模块本身不依赖 ``lan_config``，避免循环导入；由路由层在保存后显式清缓存。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_SETTINGS_FILENAME = "lan_settings.json"


def _resolve_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "app" / "fastapi_routes").is_dir() and (parent / "XCAGI").is_dir():
            return parent
    return here.parents[2]


def _settings_path() -> Path:
    override = (os.environ.get("LAN_SETTINGS_FILE") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (_resolve_repo_root() / "data" / _SETTINGS_FILENAME).resolve()


@dataclass
class LanSettingsOverride:
    """可覆写的字段。``None`` 代表"不覆写，沿用 env/默认值"。"""

    enabled: bool | None = None
    license_secret: str | None = None
    admin_bootstrap_key: str | None = None
    allowed_cidrs: list[str] | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.enabled is not None:
            out["enabled"] = bool(self.enabled)
        if self.license_secret is not None:
            out["license_secret"] = str(self.license_secret)
        if self.admin_bootstrap_key is not None:
            out["admin_bootstrap_key"] = str(self.admin_bootstrap_key)
        if self.allowed_cidrs is not None:
            out["allowed_cidrs"] = [str(x) for x in self.allowed_cidrs]
        return out

    @classmethod
    def from_json(cls, raw: Any) -> LanSettingsOverride:
        if not isinstance(raw, dict):
            return cls()
        enabled = raw.get("enabled")
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() in {"1", "true", "yes", "on"}
        elif enabled is not None:
            enabled = bool(enabled)
        secret = raw.get("license_secret")
        if secret is not None:
            secret = str(secret)
        bootstrap = raw.get("admin_bootstrap_key")
        if bootstrap is not None:
            bootstrap = str(bootstrap)
        allowed_cidrs = raw.get("allowed_cidrs")
        parsed_cidrs: list[str] | None = None
        if isinstance(allowed_cidrs, (list, tuple)):
            parsed_cidrs = [str(x).strip() for x in allowed_cidrs if str(x).strip()]
        elif isinstance(allowed_cidrs, str):
            parsed_cidrs = [x.strip() for x in allowed_cidrs.split(",") if x.strip()]
        return cls(
            enabled=enabled,
            license_secret=secret,
            admin_bootstrap_key=bootstrap,
            allowed_cidrs=parsed_cidrs,
        )


def load_overrides() -> LanSettingsOverride:
    """读取磁盘中的覆写；文件不存在或坏掉时返回空覆写（不抛错）。"""
    path = _settings_path()
    if not path.exists():
        return LanSettingsOverride()
    try:
        with _LOCK:
            raw = path.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else {}
        return LanSettingsOverride.from_json(data)
    except Exception as exc:
        logger.warning("load_overrides failed at %s: %s", path, exc)
        return LanSettingsOverride()


def save_overrides(update: LanSettingsOverride, *, merge: bool = True) -> LanSettingsOverride:
    """
    写入覆写。``merge=True`` 时与已有文件合并（仅覆盖本次显式提供的字段），
    ``merge=False`` 时整体替换。
    """
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with _LOCK:
        current = LanSettingsOverride()
        if merge and path.exists():
            try:
                raw = path.read_text(encoding="utf-8")
                if raw.strip():
                    current = LanSettingsOverride.from_json(json.loads(raw))
            except Exception:
                current = LanSettingsOverride()

        if update.enabled is not None:
            current.enabled = update.enabled
        if update.license_secret is not None:
            current.license_secret = update.license_secret
        if update.admin_bootstrap_key is not None:
            current.admin_bootstrap_key = update.admin_bootstrap_key
        if update.allowed_cidrs is not None:
            current.allowed_cidrs = [str(x).strip() for x in update.allowed_cidrs if str(x).strip()]

        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(current.to_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, path)

    return current
