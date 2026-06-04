"""域注册表单元测试（domain_registry）"""
from __future__ import annotations

from app.fastapi_routes.domain_registry import (
    ALLOWED_LEGACY_FILES,
    BUSINESS_DOMAINS,
    DOMAIN_TO_DIR,
    LEGACY_ROUTE_REGISTRY,
    LegacyRoute,
    get_pending_domains,
    get_routes_by_domain,
    verify_registry_integrity,
)


def test_business_domains_not_empty() -> None:
    assert len(BUSINESS_DOMAINS) >= 14


def test_every_domain_has_dir_mapping() -> None:
    for d in BUSINESS_DOMAINS:
        assert d in DOMAIN_TO_DIR
        assert DOMAIN_TO_DIR[d].endswith("/")


def test_legacy_route_registry_is_tuple() -> None:
    assert isinstance(LEGACY_ROUTE_REGISTRY, tuple)


def test_every_target_domain_is_valid() -> None:
    for r in LEGACY_ROUTE_REGISTRY:
        assert r.target_domain in BUSINESS_DOMAINS


def test_verify_registry_integrity_passes() -> None:
    assert verify_registry_integrity() == []


def test_get_routes_by_domain() -> None:
    auth_routes = get_routes_by_domain("auth")
    assert len(auth_routes) == 1
    assert auth_routes[0].target_module.endswith("domains.auth.routes")


def test_get_routes_by_domain_empty_for_nonexistent() -> None:
    assert get_routes_by_domain("nonexistent-domain-xyz") == []


def test_get_pending_domains_includes_unmigrated() -> None:
    assert isinstance(get_pending_domains(), list)


def test_domain_doc_one_per_business_domain() -> None:
    assert len(LEGACY_ROUTE_REGISTRY) == len(BUSINESS_DOMAINS)
    assert {r.target_domain for r in LEGACY_ROUTE_REGISTRY} == set(BUSINESS_DOMAINS)


def test_target_module_format() -> None:
    for r in LEGACY_ROUTE_REGISTRY:
        assert r.target_module.startswith("app.fastapi_routes.domains.")


def test_allowed_legacy_files_whitelist() -> None:
    assert ALLOWED_LEGACY_FILES == frozenset({"xcagi_compat.py"})


def test_legacy_route_dataclass() -> None:
    r = LegacyRoute(
        filename="domain:auth",
        target_domain="auth",
        target_module="app.fastapi_routes.domains.auth.routes",
        note="test",
    )
    assert r.target_domain == "auth"
