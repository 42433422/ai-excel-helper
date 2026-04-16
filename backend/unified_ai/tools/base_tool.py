"""
工具基类
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = ""
    message: str = ""
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "metadata": self.metadata or {}
        }


class BaseTool:
    name: str = "base_tool"
    description: str = "基础工具"

    def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError("子类必须实现 execute 方法")

    def validate_input(self, **kwargs) -> tuple[bool, str]:
        return True, ""
