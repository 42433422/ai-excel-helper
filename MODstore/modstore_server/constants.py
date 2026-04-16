"""MODstore 服务端约定常量（避免魔法数分散在入口与文档中）。"""

from modman.constants import DEFAULT_XCAGI_BACKEND_URL

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8765

__all__ = ["DEFAULT_API_HOST", "DEFAULT_API_PORT", "DEFAULT_XCAGI_BACKEND_URL"]
