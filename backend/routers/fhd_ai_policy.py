"""FHD AI policy read-only endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter

from backend.ai_model_registry import list_public_models

router = APIRouter(tags=["fhd-ai-policy"])


@router.get("/ai-tier/status")
def api_ai_tier_status() -> dict:
    secret = bool(os.environ.get("FHD_AI_ELEVATED_TOKEN", "").strip())
    strict = os.environ.get("FHD_AI_TIER_STRICT", "").strip().lower() in ("1", "true", "yes", "on")
    return {
        "elevated_token_configured": secret,
        "tier_strict": strict,
        "default_tier": "p1",
    }


@router.get("/ai/models")
def api_ai_models_public() -> dict:
    return {"success": True, "models": list_public_models()}
