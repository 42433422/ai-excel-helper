"""工作区相对路径安全解析（SDK re-export）。

``resolve_safe_workspace_relpath(rel)`` 防止 Mod 误用 ``../`` 越狱到工作区外；
始终返回一个解析到工作区根下的绝对 ``Path``，遇到越界会抛 ``ValueError``。
"""

from __future__ import annotations

from app.infrastructure.workspace import resolve_safe_workspace_relpath  # noqa: F401

__all__ = ["resolve_safe_workspace_relpath"]
