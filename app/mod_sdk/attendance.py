"""考勤转换相关能力（SDK re-export）。

供 ``taiyangniao-pro`` Mod 使用。未来任务 B 会把 ``app.shell.taiyangniao_attendance.*``
整体搬回 ``mods/taiyangniao-pro/backend/attendance/``，届时本模块可以被移除
或缩减为空壳（保留 import 面以避免 Mod 侧突然断裂）。
"""

from __future__ import annotations

from app.shell.taiyangniao_attendance.convert import convert_attendance_file  # noqa: F401
from app.shell.taiyangniao_attendance.paths import attendance_workspace_root  # noqa: F401

__all__ = ["attendance_workspace_root", "convert_attendance_file"]
