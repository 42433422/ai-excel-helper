# -*- coding: utf-8 -*-
"""里程碑 N：NeuroBus 领域事件处理器注册编排（实现委托宿主 handler 模块）。"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROVIDER_ID = "mod:xcagi-neuro-bus-bridge"
DELEGATE = "host.neuro_bus.domains"


def _catalog_path() -> Path | None:
    here = Path(__file__).resolve().parent.parent
    p = here / "config" / "neuro_handler_catalog.json"
    return p if p.is_file() else None


def load_handler_catalog() -> dict[str, Any]:
    p = _catalog_path()
    if not p:
        return {"handlers": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"handlers": []}
    except Exception:
        return {"handlers": []}


def list_handler_specs() -> list[dict[str, Any]]:
    raw = load_handler_catalog().get("handlers") or []
    if not isinstance(raw, list):
        return []
    specs: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        domain_id = str(row.get("domain_id") or "").strip()
        host_module = str(row.get("host_module") or "").strip()
        register_fn = str(row.get("register_fn") or "").strip()
        if domain_id and host_module and register_fn:
            specs.append(
                {
                    "domain_id": domain_id,
                    "host_module": host_module,
                    "register_fn": register_fn,
                    "optional": bool(row.get("optional")),
                }
            )
    return specs


def register_all_domain_handlers(bus) -> dict[str, Any]:
    """按 catalog 将宿主 *_domain_handlers 注册到 NeuroBus。"""
    registered: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []

    for spec in list_handler_specs():
        domain_id = spec["domain_id"]
        host_module = spec["host_module"]
        register_fn = spec["register_fn"]
        optional = spec.get("optional")
        try:
            mod = importlib.import_module(host_module)
            fn = getattr(mod, register_fn, None)
            if not callable(fn):
                raise AttributeError(f"{register_fn} not callable on {host_module}")
            fn(bus)
            registered.append(domain_id)
            logger.info("[NeuroBusMod] registered handlers: %s via %s", domain_id, host_module)
        except ImportError as exc:
            if optional:
                skipped.append(domain_id)
                logger.debug("[NeuroBusMod] optional handler skipped: %s (%s)", domain_id, exc)
            else:
                errors.append({"domain_id": domain_id, "error": str(exc)})
                logger.error("[NeuroBusMod] handler import failed: %s", domain_id, exc_info=True)
        except Exception as exc:
            errors.append({"domain_id": domain_id, "error": str(exc)})
            logger.error("[NeuroBusMod] handler register failed: %s", domain_id, exc_info=True)

    return {
        "provider_id": PROVIDER_ID,
        "delegate": DELEGATE,
        "registered": registered,
        "skipped_optional": skipped,
        "errors": errors,
        "handler_count": len(registered),
    }


def summarize_handler_catalog() -> dict[str, Any]:
    specs = list_handler_specs()
    return {
        "provider_id": PROVIDER_ID,
        "catalog_file": "config/neuro_handler_catalog.json",
        "handler_spec_count": len(specs),
        "domain_ids": [s["domain_id"] for s in specs],
    }


__all__ = [
    "PROVIDER_ID",
    "load_handler_catalog",
    "list_handler_specs",
    "register_all_domain_handlers",
    "summarize_handler_catalog",
]
