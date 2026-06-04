"""
domains/ — 按业务域组织的路由包（替代散落的 legacy_/xcagi_compat_）

14+ 业务域目录在 ``domains/<domain>/``；v10.0.3 已删除 legacy shim，运行时由 domains 与
``register_legacy_gap_routers`` 承载；域文档见 ``domain_registry.py``。
"""

from __future__ import annotations

__all__ = [
    "auth",
]
