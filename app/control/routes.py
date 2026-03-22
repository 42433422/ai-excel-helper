import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

bp = Blueprint("control", __name__, url_prefix="/api/control")

# 简单内存存储最新一条指令，按 target 分组
_latest_input_command: dict[str, dict] = {}


@bp.route("/input", methods=["POST"])
def post_input():
    """
    QClaw 调用：发送要填到前端输入框的内容
    """
    data = request.get_json(silent=True) or {}
    target = data.get("target", "main_input")
    text = data.get("text", "")
    action = data.get("action", "none")  # 例如: parse_and_generate / fill_only

    if not isinstance(text, str) or not text.strip():
        return (
            jsonify(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": "EMPTY_TEXT", "message": "text 不能为空"},
                }
            ),
            400,
        )

    cmd_id = uuid.uuid4().hex
    _latest_input_command[target] = {
        "id": cmd_id,
        "target": target,
        "text": text,
        "action": action,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "handled": False,
    }

    return jsonify({"success": True, "data": {"command_id": cmd_id}, "error": None})


@bp.route("/input/latest", methods=["GET"])
def get_latest_input():
    """
    前端轮询：获取某个 target 的最新未处理指令
    """
    target = request.args.get("target", "main_input")
    cmd = _latest_input_command.get(target)

    if not cmd or cmd.get("handled"):
        return jsonify({"success": True, "data": None, "error": None})

    return jsonify({"success": True, "data": cmd, "error": None})


@bp.route("/input/<cmd_id>/ack", methods=["POST"])
def ack_input(cmd_id: str):
    """
    前端处理完指令后确认，避免重复执行
    """
    target = request.args.get("target", "main_input")
    cmd = _latest_input_command.get(target)

    if not cmd or cmd.get("id") != cmd_id:
        return (
            jsonify(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "命令不存在或已过期",
                    },
                }
            ),
            404,
        )

    cmd["handled"] = True
    return jsonify({"success": True, "data": None, "error": None})

