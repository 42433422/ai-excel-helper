"""Parity: event-primary facade vs core wiring (env flag)."""

import os

from app import bootstrap
from app.application.facades.shipment_event_primary import ShipmentApplicationServiceEventPrimary
from app.application.shipment_app_service import ShipmentApplicationService


def _clear_shipment_caches():
    from app.di.registry import get_service_registry

    get_service_registry().invalidate_shipment_wiring()


def test_get_shipment_app_service_defaults_to_core():
    os.environ.pop("XCAGI_EVENT_PRIMARY", None)
    os.environ.pop("XCAGI_EVENT_PRIMARY_SHIPMENT", None)
    _clear_shipment_caches()
    svc = bootstrap.get_shipment_app_service()
    assert isinstance(svc, ShipmentApplicationService)
    assert not isinstance(svc, ShipmentApplicationServiceEventPrimary)


def test_get_shipment_app_service_event_primary_when_flagged():
    os.environ.pop("XCAGI_EVENT_PRIMARY", None)
    os.environ["XCAGI_EVENT_PRIMARY_SHIPMENT"] = "1"
    _clear_shipment_caches()
    try:
        svc = bootstrap.get_shipment_app_service()
        assert isinstance(svc, ShipmentApplicationServiceEventPrimary)
    finally:
        os.environ.pop("XCAGI_EVENT_PRIMARY_SHIPMENT", None)
        _clear_shipment_caches()
