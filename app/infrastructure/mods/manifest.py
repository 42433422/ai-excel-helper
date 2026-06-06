"""
Mod Manifest Definition and Parsing
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from .artifact_constants import ARTIFACT_MOD, normalize_artifact

logger = logging.getLogger(__name__)


@dataclass
class ModMetadata:
    id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    artifact: str = ARTIFACT_MOD
    bundle: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, str] = field(default_factory=dict)
    backend_entry: str = ""
    backend_init: str = ""
    frontend_routes: str = ""
    frontend_pro_entry_path: str = ""
    frontend_menu: list[dict[str, str]] = field(default_factory=list)
    frontend_menu_overrides: list[dict[str, Any]] = field(default_factory=list)
    config_overrides: str = ""
    hooks: dict[str, str] = field(default_factory=dict)
    comms_exports: list[str] = field(default_factory=list)
    mod_path: str = ""
    primary: bool = False
    # id / label 及 Mod 自定义字段（panel_summary、phone_agent_* 等）一并保留
    workflow_employees: list[dict[str, Any]] = field(default_factory=list)
    # Mod 声明其所属/提供的行业。结构与 resources/config/industry_config.yaml 中
    # industries[<id>] 条目对齐（name/description/units/quantity_fields/product_fields/
    # order_types/intent_keywords/print_config），额外要求顶层提供 id。
    # 行业下拉列表优先由已加载 Mod 的此字段驱动；YAML 仅作为无 Mod 环境下的回退。
    industry: dict[str, Any] = field(default_factory=dict)
    # Mod 可选 UI 文案覆盖。用于让扩展包直接决定宿主通用界面的业务词汇，
    # 例如 entity/query_title/starter_pack 等，未声明时由 industry 字段推导。
    ui_labels: dict[str, Any] = field(default_factory=dict)
    ui_starter_pack: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], mod_path: str = "") -> "ModMetadata":
        backend = data.get("backend", {})
        frontend = data.get("frontend", {})
        config = data.get("config", {})
        hooks = data.get("hooks", {})
        comms = data.get("comms", {}) or {}
        comms_exports_raw = comms.get("exports", [])
        menu_overrides_raw = frontend.get("menu_overrides", [])
        menu_overrides: list[dict[str, Any]] = []
        if isinstance(menu_overrides_raw, dict):
            for k, v in menu_overrides_raw.items():
                key = str(k or "").strip()
                if not key:
                    continue
                row = dict(v) if isinstance(v, dict) else {"label": v}
                row["key"] = key
                menu_overrides.append(row)
        elif isinstance(menu_overrides_raw, list):
            menu_overrides = [x for x in menu_overrides_raw if isinstance(x, dict)]
        comms_exports = (
            [str(x).strip() for x in comms_exports_raw if str(x).strip()]
            if isinstance(comms_exports_raw, list)
            else []
        )

        bundle_raw = data.get("bundle")
        bundle: dict[str, Any] = bundle_raw if isinstance(bundle_raw, dict) else {}

        industry_raw = data.get("industry")
        industry_block: dict[str, Any]
        if isinstance(industry_raw, dict) and industry_raw.get("id"):
            industry_block = dict(industry_raw)
        else:
            if industry_raw not in (None, {}):
                logger.warning(
                    "Mod %r industry field ignored: expected object with 'id', got %r",
                    data.get("id"),
                    type(industry_raw).__name__,
                )
            industry_block = {}

        ui_labels_raw = data.get("ui_labels")
        ui_labels = dict(ui_labels_raw) if isinstance(ui_labels_raw, dict) else {}
        ui_starter_pack_raw = data.get("ui_starter_pack")
        ui_starter_pack = (
            [x for x in ui_starter_pack_raw if isinstance(x, dict)]
            if isinstance(ui_starter_pack_raw, list)
            else []
        )

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            artifact=normalize_artifact(data),
            bundle=bundle,
            dependencies=data.get("dependencies", {}),
            backend_entry=backend.get("entry", ""),
            backend_init=backend.get("init", ""),
            frontend_routes=frontend.get("routes", ""),
            frontend_pro_entry_path=str(frontend.get("pro_entry_path", "") or "").strip(),
            frontend_menu=frontend.get("menu", []),
            frontend_menu_overrides=menu_overrides,
            config_overrides=config.get("industry_overrides", ""),
            hooks=hooks,
            comms_exports=comms_exports,
            mod_path=mod_path,
            primary=data.get("primary", False),
            workflow_employees=data.get("workflow_employees", []),
            industry=industry_block,
            ui_labels=ui_labels,
            ui_starter_pack=ui_starter_pack,
        )


def parse_manifest(mod_path: str) -> ModMetadata | None:
    manifest_path = os.path.join(mod_path, "manifest.json")
    logger.info(f"[parse_manifest] Checking manifest at: {manifest_path}")
    if not os.path.isfile(manifest_path):
        logger.warning(f"[parse_manifest] Mod manifest not found: {manifest_path}")
        return None

    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        if not data.get("id"):
            logger.error(f"[parse_manifest] Mod manifest missing 'id' field: {manifest_path}")
            return None

        metadata = ModMetadata.from_dict(data, mod_path)
        logger.info(
            f"[parse_manifest] Successfully parsed manifest for mod: {metadata.id}, name: {metadata.name}"
        )
        return metadata
    except json.JSONDecodeError as e:
        logger.error(f"[parse_manifest] Failed to parse manifest JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"[parse_manifest] Failed to read manifest: {e}")
        return None


def validate_dependencies(metadata: ModMetadata, loaded_mods: list[str]) -> bool:
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

    current_version = "8.0.0"

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
