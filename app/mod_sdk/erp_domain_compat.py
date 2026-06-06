# -*- coding: utf-8 -*-
"""里程碑 C/G：产品 / 出货 / 微信等领域 API 经 ``xcagi-erp-domain-bridge`` 门面。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

ERP_DOMAIN_BRIDGE_MOD_ID = "xcagi-erp-domain-bridge"

logger = logging.getLogger(__name__)

DOMAIN_SPECS: tuple[dict[str, Any], ...] = (
    {
        "domain_id": "products",
        "label": "产品",
        "host_prefixes": ["/api/products"],
        "facade_prefix": f"/api/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}/products",
    },
    {
        "domain_id": "customers",
        "label": "客户/购买单位",
        "host_prefixes": ["/api/customers", "/api/purchase_units"],
        "facade_prefix": f"/api/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}/customers",
    },
    {
        "domain_id": "shipment",
        "label": "出货/订单",
        "host_prefixes": ["/api/orders", "/api/shipment"],
        "facade_prefix": f"/api/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}/shipment",
    },
    {
        "domain_id": "wechat",
        "label": "微信",
        "host_prefixes": ["/api/wechat", "/api/wechat_contacts"],
        "facade_prefix": f"/api/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}/wechat",
    },
)


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(ERP_DOMAIN_BRIDGE_MOD_ID)
        if meta and meta.mod_path:
            p = Path(meta.mod_path)
            if (p / "manifest.json").is_file():
                return p
    except Exception:
        logger.debug("erp domain mod path lookup failed", exc_info=True)

    for key in ("XCAGI_MODS_ROOT", "XCAGI_MODS_DIR"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            trial = Path(raw) / ERP_DOMAIN_BRIDGE_MOD_ID
            if (trial / "manifest.json").is_file():
                return trial

    repo = Path(__file__).resolve().parents[2] / "mods" / ERP_DOMAIN_BRIDGE_MOD_ID
    if (repo / "manifest.json").is_file():
        return repo
    return None


def _read_manifest() -> dict[str, Any]:
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return {}
    try:
        data = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_erp_domain_mod_installed() -> bool:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

        if is_mods_disabled():
            return False
        for row in get_mod_manager().list_all_mods():
            if str(row.get("id") or "").strip() == ERP_DOMAIN_BRIDGE_MOD_ID:
                return True
    except Exception:
        pass
    return _resolve_mod_dir() is not None


def is_erp_domain_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_ERP_DOMAIN_MOD"):
        return False
    if _truthy_env("XCAGI_ERP_DOMAIN_VIA_MOD"):
        return True
    if not is_erp_domain_mod_installed():
        return False
    cfg = _read_manifest().get("config") or {}
    if not isinstance(cfg, dict):
        return False
    if cfg.get("erp_domain_facade") is True:
        return True
    inner = cfg.get("erp_domains") or {}
    return isinstance(inner, dict) and inner.get("facade_enabled") is True


def load_erp_domains_config() -> dict[str, Any]:
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return {}
    path = mod_dir / "config" / "erp_domains.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.warning("erp_domains.json parse failed")
        return {}


def _mod_handler_domains() -> set[str]:
    try:
        cfg = _read_manifest().get("config") or {}
        raw = cfg.get("mod_domain_handlers") or cfg.get("erp_domain_handlers") or []
        if isinstance(raw, list):
            return {str(x).strip() for x in raw if str(x).strip()}
    except Exception:
        pass
    return set()


def list_erp_domains_registry() -> dict[str, Any]:
    via_mod = is_erp_domain_via_mod_enabled()
    handler_domains = _mod_handler_domains()
    domains = []
    for spec in DOMAIN_SPECS:
        dom_id = str(spec.get("domain_id") or "")
        if dom_id in handler_domains:
            delegate = "mod.domain_handlers"
        elif via_mod:
            delegate = "host.fastapi_routes"
        else:
            delegate = "host.fastapi_routes"
        domains.append(
            {
                **spec,
                "facade_enabled": via_mod,
                "delegate": delegate,
                "mod_domain_handler": dom_id in handler_domains,
            }
        )
    handlers_on = bool(handler_domains) and via_mod
    return {
        "ok": True,
        "mod_id": ERP_DOMAIN_BRIDGE_MOD_ID,
        "domain_count": len(domains),
        "domains": domains,
        "execution_via_mod_facade": via_mod,
        "execution_path": (
            "mod_domain_handler" if handlers_on else ("mod_facade" if via_mod else "host.api")
        ),
        "mod_domain_handler_domains": sorted(handler_domains),
        "registry_endpoint": f"/api/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}/domains/registry",
        "note": (
            "里程碑 G2：产品/客户/出货/微信 handler 均在 Mod backend；DB/Service 仍宿主。"
            if handlers_on
            else (
                "里程碑 C：领域 HTTP 入口在 Mod；handler 仍委托宿主路由。"
                if via_mod
                else "安装 xcagi-erp-domain-bridge 且 erp_domain_facade=true 后启用。"
            )
        ),
    }


def resolve_host_api_path(facade_path: str) -> str:
    """将 Mod 门面路径映射回宿主 /api/*（供内部文档与测试）。"""
    prefix = f"/api/mod/{ERP_DOMAIN_BRIDGE_MOD_ID}"
    if facade_path.startswith(prefix):
        rest = facade_path[len(prefix) :]
        return f"/api{rest}"
    return facade_path


__all__ = [
    "DOMAIN_SPECS",
    "ERP_DOMAIN_BRIDGE_MOD_ID",
    "is_erp_domain_mod_installed",
    "is_erp_domain_via_mod_enabled",
    "list_erp_domains_registry",
    "load_erp_domains_config",
    "resolve_host_api_path",
]
