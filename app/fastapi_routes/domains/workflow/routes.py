"""Registry 兼容：xcagi compat 聚合入口在 ``app.fastapi_routes.xcagi_compat``。"""

from __future__ import annotations

from app.fastapi_routes.xcagi_compat import router  # noqa: F401

__all__ = ["router"]
