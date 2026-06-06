"""客户端运行时开关（SDK re-export）。

``read_client_mods_off_state()`` 返回布尔，表示前端是否启用了"原版模式"
（关闭所有 Mod 扩展）。Mod 的长驻任务启动前应该读一下，若为 True 就让出控制权。
"""

from __future__ import annotations

from app.fastapi_routes.state import read_client_mods_off_state  # noqa: F401

__all__ = ["read_client_mods_off_state"]
