"""CI fixture: FastAPI routes for modman blueprint_scan tests."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/hello")
def hello():
    return "ok"


@router.get("/attendance/rules")
def attendance_rules():
    return []
