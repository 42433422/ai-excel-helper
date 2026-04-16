"""FastAPI 子路由（XCAGI 兼容与壳层）。"""

from backend.routers.xcagi_compat import router as xcagi_compat_router
from backend.routers.xcagi_shell import router as xcagi_shell_router

__all__ = ["xcagi_compat_router", "xcagi_shell_router"]
