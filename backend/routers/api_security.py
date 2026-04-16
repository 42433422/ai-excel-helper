"""与 AuditMiddleware 共用的「公开 /api 路径」判定（免 API Key）。"""

from __future__ import annotations

# 前缀匹配（path_norm 已 rstrip('/')，根路径为 "/"）
API_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/state/",
    "/api/traditional-mode/",
    "/api/fhd/",
    "/api/system/",
    "/api/products/",
    "/api/templates/",
    "/api/wechat_contacts/",
    "/api/conversations/",
    "/api/ai/",
    "/api/tts/",
    "/api/purchase_units",
    "/api/customers",
    "/api/preferences",
    "/api/distillation/",
    "/api/intent-packages",
    "/api/intent_packages",
    "/api/mods/",
    "/api/startup/",
    "/api/shipment/",
    "/api/sales-contract/",
    "/api/document-templates",
    "/api/model-payment/",
    "/api/mod-store/",
    "/api/code-editor/",
)

API_PUBLIC_EXACT: frozenset[str] = frozenset(
    {
        "/api/health",
        "/api/mods",
        "/api/tools",
        "/api/db-tools",
        "/api/tool-categories",
    }
)


def is_api_public_path(path_norm: str) -> bool:
    if path_norm in API_PUBLIC_EXACT:
        return True
    return any(path_norm.startswith(p) for p in API_PUBLIC_PREFIXES)
