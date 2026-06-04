# -*- coding: utf-8 -*-
"""神经域落地计划：注册表、NeuroUnitOfWork、协调器异常路径意图事件。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.domain.neuro.neuro_uow import NeuroUnitOfWork
from app.domain.neuro.processors.coordinator import (
    ProcessorCoordinator,
    ProcessorType,
    RoutingDecision,
)
from app.neuro_bus.register_all_neuro_domains import register_all_neuro_domains


def test_register_all_neuro_domains_includes_shipment():
    names = register_all_neuro_domains()
    assert "shipment" in names
    assert "intent" in names


def test_neuro_uow_runs_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    factory = sessionmaker(bind=engine)
    with NeuroUnitOfWork(session_factory=factory) as session:
        session.execute(text("SELECT 1"))


@pytest.mark.asyncio
async def test_coordinator_exception_triggers_emit_intent_event():
    coord = ProcessorCoordinator()
    decision = RoutingDecision(
        processor_type=ProcessorType.CONSCIOUS,
        confidence=0.5,
        reason="test",
    )
    with patch.object(coord, "route", return_value=decision):
        with patch.object(coord, "_process_conscious", side_effect=RuntimeError("boom")):
            with patch.object(coord, "_process_reflex", side_effect=RuntimeError("no reflex")):
                with patch.object(coord, "_emit_intent_event", new_callable=AsyncMock) as em:
                    report = await coord.process("hello", "user1", {})
                    assert report.success is False
                    em.assert_awaited()


def test_neuro_domains_package_imports():
    from app.neuro_domains import (
        NeuroUnitOfWork,
        ShipmentNeuroDomain,
        get_processor_coordinator,
        get_shipment_domain,
    )

    assert ShipmentNeuroDomain.domain_name == "shipment"
    assert get_shipment_domain() is not None
    assert get_processor_coordinator() is not None
    assert NeuroUnitOfWork is not None
