"""
Example Mod Blueprints
"""

import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

_example_bp = None


def create_blueprint(mod_id: str):
    bp = Blueprint(mod_id, __name__, url_prefix=f"/api/mod/{mod_id}")

    @bp.route("/hello", methods=["GET"])
    def hello():
        return jsonify({
            "success": True,
            "data": {
                "message": f"Hello from {mod_id}!",
                "version": "1.0.0"
            }
        })

    @bp.route("/status", methods=["GET"])
    def status():
        return jsonify({
            "success": True,
            "data": {
                "mod_id": mod_id,
                "status": "running"
            }
        })

    return bp


def register_blueprints(app, mod_id: str):
    global _example_bp
    _example_bp = create_blueprint(mod_id)
    app.register_blueprint(_example_bp)
    logger.info(f"Example mod blueprints registered for: {mod_id}")


def _comms_ping(*args, **kwargs):
    """供其他 Mod 通过 get_mod_comms().call(..., 'example-mod', 'ping', ...) 调用。"""
    from app.infrastructure.mods.comms import get_caller_mod_id

    return {
        "pong": True,
        "mod": "example-mod",
        "caller": get_caller_mod_id(),
        "args": args,
        "kwargs": kwargs,
    }


def mod_init():
    logger.info("Example mod initialized")
    try:
        from app.infrastructure.mods.comms import get_mod_comms

        get_mod_comms().register("example-mod", "ping", _comms_ping, replace=True)
    except Exception as e:
        logger.warning("example-mod comms register skipped: %s", e)
