"""
Client State API
用于前端与后端同步原版模式等客户端状态
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

bp = Blueprint("state", __name__, url_prefix="/api/state")

STATE_FILE = Path(__file__).parent.parent / ".client_mods_state.json"


def get_state_file_path():
    return STATE_FILE


def read_client_mods_off_state() -> bool:
    """读取状态文件，返回 client_mods_off 值"""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data.get("client_mods_off", False)
    except Exception as e:
        logger.warning(f"[State API] 读取状态文件失败: {e}")
    return False


def write_client_mods_off_state(value: bool) -> None:
    """写入状态文件"""
    try:
        data = {
            "client_mods_off": value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[State API] 已写入 client_mods_off={value}")
    except Exception as e:
        logger.error(f"[State API] 写入状态文件失败: {e}")


@bp.route("/client-mods-off", methods=["GET"])
def get_client_mods_off():
    """获取当前 client_mods_off 状态"""
    return jsonify({
        "success": True,
        "data": {
            "client_mods_off": read_client_mods_off_state()
        }
    })


@bp.route("/client-mods-off", methods=["POST"])
def set_client_mods_off():
    """设置 client_mods_off 状态"""
    body = request.get_json(silent=True) or {}
    value = bool(body.get("client_mods_off", False))
    write_client_mods_off_state(value)
    return jsonify({
        "success": True,
        "data": {
            "client_mods_off": value
        }
    })
