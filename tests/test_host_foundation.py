# -*- coding: utf-8 -*-

from app.mod_sdk.host_foundation import (
    HOST_FOUNDATION_EMPLOYEE_PACK_ID,
    catalog_store_collection,
    host_foundation_catalog_row,
    is_host_foundation_employee_pack,
    is_infrastructure_mod_hidden_from_store,
)


def test_bridge_hidden_from_store():
    assert is_infrastructure_mod_hidden_from_store("xcagi-planner-bridge")
    assert is_infrastructure_mod_hidden_from_store("xcagi-workflow-employee-phone")
    assert not is_infrastructure_mod_hidden_from_store(HOST_FOUNDATION_EMPLOYEE_PACK_ID)


def test_host_foundation_catalog_row():
    row = host_foundation_catalog_row(installed=False)
    assert row["id"] == HOST_FOUNDATION_EMPLOYEE_PACK_ID
    assert row["artifact"] == "employee_pack"
    assert catalog_store_collection(row) == "host_foundation"


def test_is_host_foundation_employee_pack():
    assert is_host_foundation_employee_pack(HOST_FOUNDATION_EMPLOYEE_PACK_ID)
    assert not is_host_foundation_employee_pack("xcagi-planner-bridge")
