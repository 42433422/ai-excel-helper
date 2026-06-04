"""编制内员工包名单：不出现在公网 index.json。"""
from __future__ import annotations

from modstore_server.catalog_store import norm_pkg_id

# 与 tests/test_catalog_public_index.py 及 AI 市场编制策略对齐
_PLANNED_DUTY_EMPLOYEE_IDS: frozenset[str] = frozenset(
    {
        "change-request-auditor",
    }
)


def all_planned_employee_ids() -> set[str]:
    return set(_PLANNED_DUTY_EMPLOYEE_IDS)


def is_planned_duty_employee_pack(pkg_id: str, artifact: str) -> bool:
    if str(artifact or "").strip().lower() != "employee_pack":
        return False
    return norm_pkg_id(pkg_id) in _PLANNED_DUTY_EMPLOYEE_IDS
