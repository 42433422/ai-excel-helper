# -*- coding: utf-8 -*-
"""远端 Catalog 可见性过滤。"""

from app.services.catalog_visibility import is_planned_duty_employee_pack, is_public_catalog_row


def test_duty_roster_employee_pack_hidden():
    assert is_planned_duty_employee_pack("security-secrets-guard", "employee_pack")
    assert not is_public_catalog_row(
        {
            "id": "security-secrets-guard",
            "version": "1.0.0",
            "artifact": "employee_pack",
            "stored_filename": "security-secrets-guard-1.0.0.xcemp",
            "download_url": "/v1/packages/security-secrets-guard/1.0.0/download",
        }
    )


def test_duty_roster_hidden_even_when_artifact_is_mod():
    assert not is_public_catalog_row(
        {
            "id": "test-qa-runner",
            "version": "2.0.3",
            "artifact": "mod",
            "download_url": "/v1/packages/test-qa-runner/2.0.3/download",
            "public_listing": True,
        }
    )


def test_unlisted_employee_pack_hidden_without_public_listing():
    assert not is_public_catalog_row(
        {
            "id": "some-custom-employee",
            "version": "1.0.0",
            "artifact": "employee_pack",
            "stored_filename": "some-custom-employee-1.0.0.xcemp",
        }
    )


def test_public_listing_employee_pack_visible():
    assert is_public_catalog_row(
        {
            "id": "some-custom-employee",
            "version": "1.0.0",
            "artifact": "employee_pack",
            "public_listing": True,
            "download_url": "/v1/packages/some-custom-employee/1.0.0/download",
        }
    )
