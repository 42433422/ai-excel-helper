# -*- coding: utf-8 -*-
"""里程碑 J：模型付费 API 经 ``xcagi-model-payment-bridge`` 门面。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

MODEL_PAYMENT_BRIDGE_MOD_ID = "xcagi-model-payment-bridge"

logger = logging.getLogger(__name__)

HOST_PREFIX = "/api/model-payment"
FACADE_PREFIX = f"/api/mod/{MODEL_PAYMENT_BRIDGE_MOD_ID}/model-payment"


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(MODEL_PAYMENT_BRIDGE_MOD_ID)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / MODEL_PAYMENT_BRIDGE_MOD_ID
    return trial if (trial / "manifest.json").is_file() else None


def _read_manifest() -> dict[str, Any]:
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return {}
    try:
        data = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_model_payment_mod_installed() -> bool:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled

        if is_mods_disabled():
            return False
        for row in get_mod_manager().list_all_mods():
            if str(row.get("id") or "").strip() == MODEL_PAYMENT_BRIDGE_MOD_ID:
                return True
    except Exception:
        pass
    return _resolve_mod_dir() is not None


def is_model_payment_via_mod_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_MODEL_PAYMENT_MOD"):
        return False
    if _truthy_env("XCAGI_MODEL_PAYMENT_VIA_MOD"):
        return True
    if not is_model_payment_mod_installed():
        return False
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("model_payment_facade") is True:
        return True
    return False


def list_model_payment_facade_registry() -> dict[str, Any]:
    via = is_model_payment_via_mod_enabled()
    endpoints = [
        "GET /model-payment/plans",
        "POST /model-payment/checkout",
        "POST /model-payment/notify/alipay",
        "GET /model-payment/diagnostics",
        "GET /model-payment/entitlements",
        "GET /model-payment/query/{out_trade_no}",
        "POST /model-payment/refund",
        "POST /model-payment/close",
        "GET /model-payment/refund/query",
    ]
    return {
        "ok": True,
        "mod_id": MODEL_PAYMENT_BRIDGE_MOD_ID,
        "host_prefix": HOST_PREFIX,
        "facade_prefix": FACADE_PREFIX,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "execution_via_mod_facade": via,
        "execution_path": "mod_facade" if via else "host.api",
        "delegate": "app.fastapi_routes.model_payment",
        "phase": "J",
        "note": "里程碑 J：模型付费 HTTP 入口在 Mod；支付 SDK 与订单存储仍在宿主。",
    }


__all__ = [
    "FACADE_PREFIX",
    "HOST_PREFIX",
    "MODEL_PAYMENT_BRIDGE_MOD_ID",
    "is_model_payment_mod_installed",
    "is_model_payment_via_mod_enabled",
    "list_model_payment_facade_registry",
]
