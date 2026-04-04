"""
Mod Manifest Definition and Parsing
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModMetadata:
    id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    dependencies: Dict[str, str] = field(default_factory=dict)
    backend_entry: str = ""
    backend_init: str = ""
    frontend_routes: str = ""
    frontend_menu: List[Dict[str, str]] = field(default_factory=list)
    config_overrides: str = ""
    hooks: Dict[str, str] = field(default_factory=dict)
    comms_exports: List[str] = field(default_factory=list)
    mod_path: str = ""
    primary: bool = False
    # id / label 及 Mod 自定义字段（panel_summary、phone_agent_* 等）一并保留
    workflow_employees: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], mod_path: str = "") -> "ModMetadata":
        backend = data.get("backend", {})
        frontend = data.get("frontend", {})
        config = data.get("config", {})
        hooks = data.get("hooks", {})
        comms = data.get("comms", {}) or {}
        comms_exports_raw = comms.get("exports", [])
        comms_exports = (
            [str(x).strip() for x in comms_exports_raw if str(x).strip()]
            if isinstance(comms_exports_raw, list)
            else []
        )

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", {}),
            backend_entry=backend.get("entry", ""),
            backend_init=backend.get("init", ""),
            frontend_routes=frontend.get("routes", ""),
            frontend_menu=frontend.get("menu", []),
            config_overrides=config.get("industry_overrides", ""),
            hooks=hooks,
            comms_exports=comms_exports,
            mod_path=mod_path,
            primary=data.get("primary", False),
            workflow_employees=data.get("workflow_employees", []),
        )


def parse_manifest(mod_path: str) -> Optional[ModMetadata]:
    manifest_path = os.path.join(mod_path, "manifest.json")
    logger.info(f"[parse_manifest] Checking manifest at: {manifest_path}")
    if not os.path.isfile(manifest_path):
        logger.warning(f"[parse_manifest] Mod manifest not found: {manifest_path}")
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data.get("id"):
            logger.error(f"[parse_manifest] Mod manifest missing 'id' field: {manifest_path}")
            return None

        metadata = ModMetadata.from_dict(data, mod_path)
        logger.info(f"[parse_manifest] Successfully parsed manifest for mod: {metadata.id}, name: {metadata.name}")
        return metadata
    except json.JSONDecodeError as e:
        logger.error(f"[parse_manifest] Failed to parse manifest JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"[parse_manifest] Failed to read manifest: {e}")
        return None


def validate_dependencies(metadata: ModMetadata, loaded_mods: List[str]) -> bool:
    for dep_id, version_spec in metadata.dependencies.items():
        if dep_id == "xcagi":
            if not _check_xcagi_version(version_spec):
                return False
        elif dep_id not in loaded_mods:
            logger.warning(
                f"Mod {metadata.id} depends on {dep_id} which is not loaded. "
                f"Required version: {version_spec}"
            )
            return False
    return True


def _check_xcagi_version(version_spec: str) -> bool:
    import re
    current_version = "1.0.0"

    match = re.match(r">=([\d.]+)", version_spec)
    if match:
        required = match.group(1)
        return _compare_versions(current_version, required) >= 0

    return True


def _compare_versions(v1: str, v2: str) -> int:
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]
    for p1, p2 in zip(parts1, parts2):
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    return 0