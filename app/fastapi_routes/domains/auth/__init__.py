"""
按业务域自动发现路由的占位包。

本包当前为迁移目标（target_module）。legacy_/xcagi_compat_ 文件在迁移完成前
继续工作；本包提供目标位置和 SSOT 注册表。

迁移步骤（每个域）：
  1. 在本包下创建 routes.py / helpers.py
  2. 从对应 legacy_/xcagi_compat_ 文件中迁移路由
  3. 启动 lifespan 中改为优先注册本包路由，再 fallback 到 legacy
  4. legacy 文件加 deprecation banner
  5. 全部路由迁完后，删除 legacy_*.py
"""

from . import routes as _routes  # noqa: F401  (re-exported for type checkers)

__all__ = ["auth", "routes"]
