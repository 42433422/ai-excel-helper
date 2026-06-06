"""公网 index.json 与市场上架状态对齐。"""

from modstore_server.catalog_public_index import package_row_eligible_for_public_index


def test_duty_employee_not_in_public_index():
    row = {
        "id": "change-request-auditor",
        "version": "1.0.0",
        "artifact": "employee_pack",
        "stored_filename": "change-request-auditor-1.0.0.xcemp",
        "release_channel": "stable",
    }
    assert not package_row_eligible_for_public_index(row, public_pkg_ids={"change-request-auditor"})
    assert not package_row_eligible_for_public_index(row, public_pkg_ids=set())


def test_mod_requires_public_flag_when_db_known():
    row = {
        "id": "industry-demo-mod",
        "version": "1.0.0",
        "artifact": "mod",
        "stored_filename": "industry-demo-mod-1.0.0.xcmod",
    }
    assert not package_row_eligible_for_public_index(row, public_pkg_ids=set())
    assert package_row_eligible_for_public_index(row, public_pkg_ids={"industry-demo-mod"})
