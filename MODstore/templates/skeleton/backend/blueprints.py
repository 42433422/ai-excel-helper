"""__MOD_NAME__ — 最小蓝图（可由 modman 脚手架生成后自行扩展）"""

import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)


def create_blueprint(mod_id: str):
    bp = Blueprint(mod_id, __name__, url_prefix=f"/api/mod/{mod_id}")

    @bp.route("/hello", methods=["GET"])
    def hello():
        return jsonify(
            {
                "success": True,
                "data": {"message": f"Hello from {mod_id}", "mod": "__MOD_ID__"},
            }
        )

    return bp


def register_blueprints(app, mod_id: str):
    app.register_blueprint(create_blueprint(mod_id))
    logger.info("Mod blueprints registered: %s", mod_id)


def mod_init():
    logger.info("Mod __MOD_ID__ initialized")
