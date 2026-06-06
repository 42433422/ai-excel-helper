"""
Mod Authentication and Context Management

Enhances the original Mod isolation to prevent header forgery using HMAC signatures.
This addresses the critical security issue where any client could fake X-XCAGI-Active-Mod-Id.

Usage:
    from app.infrastructure.mods.mod_auth import ModContext, mod_context_middleware
"""

import hashlib
import hmac
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request
from starlette.requests import Request as StarletteRequest
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

# Secret for signing Mod IDs. Must be set in environment for production.
MOD_SIGNATURE_SECRET = os.environ.get("XCAGI_MOD_SIGNATURE_SECRET", "")
_MOD_API_PATH_RE = re.compile(r"^/api/mod/([^/?#]+)(?:/|$)")


@dataclass
class ModContext:
    """Enhanced Mod context with verification status and permissions."""

    mod_id: str | None = None
    verified: bool = False
    permissions: list[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def from_request(cls, request: Request) -> "ModContext":
        """Extract and verify Mod context from request headers."""
        ctx = cls()

        mod_id = request.headers.get("X-XCAGI-Active-Mod-Id") or request.headers.get(
            "x-xcagi-active-mod-id"
        )
        signature = request.headers.get("X-XCAGI-Mod-Signature") or request.headers.get(
            "x-xcagi-mod-signature"
        )

        if not mod_id:
            return ctx  # No Mod context

        normalized_mod_id = cls._normalize_mod_id(mod_id)
        if not normalized_mod_id:
            logger.warning("Invalid Mod ID format: %s", mod_id)
            return ctx

        ctx.mod_id = normalized_mod_id

        # Verify signature if secret is configured
        if MOD_SIGNATURE_SECRET:
            if signature:
                expected = cls._generate_signature(normalized_mod_id)
                ctx.verified = hmac.compare_digest(expected, signature)
                if not ctx.verified:
                    logger.warning(
                        "Mod signature verification failed for mod_id: %s", normalized_mod_id
                    )
            else:
                logger.warning("Mod ID provided without signature: %s", normalized_mod_id)
        else:
            # Development mode - accept without signature but log warning
            ctx.verified = True
            logger.debug(
                "Development mode: Mod %s accepted without signature verification",
                normalized_mod_id,
            )

        if ctx.verified:
            ctx.permissions = cls._load_mod_permissions(normalized_mod_id)
            ctx.metadata = {"source": "header", "verified_at": "now"}
            logger.info("Mod context activated: %s (verified=%s)", normalized_mod_id, ctx.verified)

        return ctx

    @staticmethod
    def _normalize_mod_id(mod_id: str) -> str | None:
        """Normalize and validate Mod ID."""
        if not mod_id:
            return None
        v = str(mod_id).strip()
        # Same regex as request_active_mod_ctx.py
        import re

        if re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", v):
            return v
        return None

    @staticmethod
    def _generate_signature(mod_id: str) -> str:
        """Generate HMAC signature for Mod ID."""
        if not MOD_SIGNATURE_SECRET:
            return ""
        message = mod_id.encode("utf-8")
        key = MOD_SIGNATURE_SECRET.encode("utf-8")
        return hmac.new(key, message, hashlib.sha256).hexdigest()[:32]

    @staticmethod
    def _load_mod_permissions(mod_id: str) -> list[str]:
        """Load permissions for a Mod. In production, this would query DB or config."""
        # Placeholder - in real implementation, load from database or manifest.json
        default_permissions = ["read:products", "read:customers", "write:shipments"]
        if mod_id.startswith("admin"):
            default_permissions.append("admin:*")
        return default_permissions

    def can_access(self, resource: str) -> bool:
        """Check if this Mod has permission for the given resource."""
        if not self.verified or not self.mod_id:
            return False
        return resource in self.permissions or any(p.startswith("admin:") for p in self.permissions)

    def is_verified(self) -> bool:
        """Return whether the Mod context was cryptographically verified."""
        return self.verified


class ModContextMiddleware:
    """注入 ``request.state.mod_context``；纯 ASGI 实现，避免 ``BaseHTTPMiddleware`` 的流式响应问题。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @staticmethod
    def _mod_context_from_path(path: str) -> ModContext:
        """无 header 时，从 /api/mod/{mod_id}/... 推断数据库上下文。"""
        match = _MOD_API_PATH_RE.match(str(path or ""))
        if not match:
            return ModContext()
        mod_id = ModContext._normalize_mod_id(match.group(1))
        if not mod_id:
            return ModContext()
        return ModContext(
            mod_id=mod_id,
            verified=False,
            metadata={"source": "path"},
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = StarletteRequest(scope, receive)
        mod_context = ModContext()
        token = None
        try:
            mod_context = ModContext.from_request(request)
            if not mod_context.mod_id:
                mod_context = self._mod_context_from_path(str(scope.get("path") or ""))
            if mod_context.mod_id:
                try:
                    cookie_name = os.environ.get("SESSION_COOKIE_NAME", "session_id")
                    sid = (request.cookies.get(cookie_name) or "").strip()
                    if sid:
                        from app.enterprise.mod_entitlements import (
                            enterprise_mod_filter_active,
                            sync_entitlements_for_session,
                        )

                        if enterprise_mod_filter_active():
                            await sync_entitlements_for_session(sid)
                    from app.infrastructure.mods.mod_manager import ensure_mod_api_ready

                    ensure_mod_api_ready(mod_context.mod_id, session_id=sid or None)
                except Exception as exc:
                    logger.warning(
                        "ensure_mod_api_ready(%s) failed: %s",
                        mod_context.mod_id,
                        exc,
                    )
            request.state.mod_context = mod_context
            from app.request_active_mod_ctx import set_request_active_mod_id

            token = set_request_active_mod_id(mod_context.mod_id)
        except (ValueError, TypeError) as e:
            logger.warning("Mod context parsing error: %s", e)
            request.state.mod_context = mod_context
        except RuntimeError as e:
            logger.error("Mod context runtime error: %s", e)
            request.state.mod_context = mod_context
        try:
            await self.app(scope, receive, send)
        finally:
            if token:
                from app.request_active_mod_ctx import reset_request_active_mod_id

                reset_request_active_mod_id(token)


def get_mod_context(request: Request) -> ModContext:
    """Get ModContext from request.state (for use in dependencies)."""
    return getattr(request.state, "mod_context", ModContext())


def require_verified_mod(request: Request) -> ModContext:
    """FastAPI dependency that requires a verified Mod context."""
    ctx = get_mod_context(request)
    if not ctx.mod_id or not ctx.is_verified():
        raise HTTPException(
            status_code=403,
            detail="Valid Mod authentication required. Please provide X-XCAGI-Mod-Signature header.",
        )
    return ctx
