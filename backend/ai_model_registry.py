"""
Public model registry metadata (no secrets).

Set FHD_PUBLIC_MODEL_REGISTRY_JSON to a JSON array, e.g.
[{"id":"deepseek-chat","provider":"deepseek","label":"DeepSeek Chat"}]
"""

from __future__ import annotations

import json
import os
from typing import Any

from backend.llm_config import resolve_chat_model, resolve_mode


def _parse_registry_json() -> list[dict[str, Any]] | None:
    raw = os.environ.get("FHD_PUBLIC_MODEL_REGISTRY_JSON", "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    out: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        mid = str(row.get("id") or row.get("model_id") or "").strip()
        if not mid:
            continue
        out.append(
            {
                "id": mid,
                "provider": str(row.get("provider") or "custom").strip() or "custom",
                "label": str(row.get("label") or mid).strip() or mid,
            }
        )
    return out or None


def list_public_models() -> list[dict[str, Any]]:
    parsed = _parse_registry_json()
    if parsed:
        return parsed
    mid = resolve_chat_model()
    return [{"id": mid, "provider": resolve_mode(), "label": mid}]
