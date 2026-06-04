"""CI fixture: Flask-style routes for modman blueprint_scan tests."""
from flask import Blueprint

bp = Blueprint("taiyangniao_fixture", __name__)


@bp.route("/hello", methods=["GET"])
def hello():
    return "ok"


@bp.route("/attendance/rules", methods=["GET"])
def attendance_rules():
    return []
