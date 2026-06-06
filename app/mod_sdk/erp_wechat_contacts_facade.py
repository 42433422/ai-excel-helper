# -*- coding: utf-8 -*-
"""里程碑 H：遗留 ``/api/wechat_contacts/*`` 经 ERP 领域 Mod 门面代理。"""

from __future__ import annotations

import os

from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, _read_manifest

MOD_SOURCE = f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def is_wechat_contacts_via_erp_facade_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_WECHAT_CONTACTS_ERP_FACADE"):
        return False
    if _truthy_env("XCAGI_WECHAT_CONTACTS_ERP_FACADE"):
        return True
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("wechat_contacts_via_facade") is True:
        return True
    return False


def tag_legacy_response(out: object) -> object:
    if isinstance(out, dict) and "source" not in out:
        tagged = dict(out)
        tagged["source"] = MOD_SOURCE
        tagged["execution_path"] = "wechat_contacts_facade"
        return tagged
    return out


__all__ = [
    "is_wechat_contacts_via_erp_facade_enabled",
    "tag_legacy_response",
]
