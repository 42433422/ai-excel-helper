"""
Control「输入命令」进程内状态与操作（无 Web 框架依赖）。

供 FastAPI 控制面路由共用。
"""

from __future__ import annotations

import uuid
from typing import Any

from app.utils.time import utc_now_iso_z

# target -> 最近一次未 ack 的命令
_latest_input_command: dict[str, dict] = {}


def enqueue_control_input(
    *, target: str, text: str, action: str
) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(text, str) or not text.strip():
        return (
            False,
            "EMPTY_TEXT",
            {
                "success": False,
                "data": None,
                "error": {"code": "EMPTY_TEXT", "message": "text 不能为空"},
            },
        )
    cmd_id = uuid.uuid4().hex
    _latest_input_command[target] = {
        "id": cmd_id,
        "target": target,
        "text": text,
        "action": action,
        "created_at": utc_now_iso_z(),
        "handled": False,
    }
    return True, cmd_id, {"success": True, "data": {"command_id": cmd_id}, "error": None}


def peek_latest_control_input(target: str) -> dict[str, Any]:
    cmd = _latest_input_command.get(target)
    if not cmd or cmd.get("handled"):
        return {"success": True, "data": None, "error": None}
    return {"success": True, "data": cmd, "error": None}


def ack_control_input(target: str, cmd_id: str) -> tuple[bool, dict[str, Any]]:
    cmd = _latest_input_command.get(target)
    if not cmd or cmd.get("id") != cmd_id:
        return False, {
            "success": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "命令不存在或已过期"},
        }
    cmd["handled"] = True
    return True, {"success": True, "data": None, "error": None}
