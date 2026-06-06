"""
Event-primary facade: mutating shipment operations go through NeuroBus commands + handlers.
Read/query methods delegate to the core application service via __getattr__.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.application.shipment_app_service import ShipmentApplicationService
from app.contexts.flags import is_event_primary_enabled
from app.neuro_async_bridge import run_coroutine_on_neuro_loop
from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.command_gateway import get_command_gateway
from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


class ShipmentApplicationServiceEventPrimary:
    def __init__(self, core: ShipmentApplicationService) -> None:
        self._core = core

    def __getattr__(self, name: str):
        return getattr(self._core, name)

    async def _dispatch_command(
        self, event_type: str, payload: dict, timeout: float = 120.0
    ) -> Any:
        gw = get_command_gateway()
        bus = get_neuro_bus()
        evt = NeuroEvent(event_type=event_type, payload=dict(payload), priority=EventPriority.HIGH)
        rid = gw.prepare_command_event(evt)
        if not bus.publish(evt):
            gw.cancel_pending(rid)
            return {"success": False, "message": "NeuroBus 未运行或无法入队"}
        try:
            return await gw.wait_for_result(rid, timeout=timeout)
        except TimeoutError:
            return {"success": False, "message": "发货操作超时"}

    def _run_cmd(self, coro):
        try:
            return run_coroutine_on_neuro_loop(coro, timeout=120.0)
        except Exception as e:
            logger.exception("event-primary shipment command failed: %s", e)
            return {"success": False, "message": str(e)}

    def create_shipment(
        self,
        unit_name: str,
        items_data: list[dict[str, Any]],
        contact_person: str = "",
        contact_phone: str = "",
    ) -> dict[str, Any]:
        if not is_event_primary_enabled("shipment"):
            return self._core.create_shipment(unit_name, items_data, contact_person, contact_phone)
        payload = {
            "shipment_id": f"PENDING-{uuid.uuid4().hex[:12]}",
            "unit_name": unit_name,
            "items": items_data,
            "contact_person": contact_person,
            "contact_phone": contact_phone,
            "deduct_inventory": True,
        }
        return self._run_cmd(self._dispatch_command("shipment.created", payload))

    def cancel_shipment(self, shipment_id: int) -> dict[str, Any]:
        if not is_event_primary_enabled("shipment"):
            return self._core.cancel_shipment(shipment_id)
        return self._run_cmd(
            self._dispatch_command(
                "shipment.cancelled",
                {"shipment_id": shipment_id, "reason": "user", "restore_inventory": True},
            )
        )

    def delete_shipment(self, shipment_id: int) -> dict[str, Any]:
        if not is_event_primary_enabled("shipment"):
            return self._core.delete_shipment(shipment_id)
        return self._run_cmd(
            self._dispatch_command("shipment.deleted", {"shipment_id": shipment_id})
        )

    def mark_as_printed(self, shipment_id: int, printer_name: str = "") -> dict[str, Any]:
        if not is_event_primary_enabled("shipment"):
            return self._core.mark_as_printed(shipment_id, printer_name)
        return self._run_cmd(
            self._dispatch_command(
                "shipment.printed",
                {
                    "shipment_id": shipment_id,
                    "printer_name": printer_name,
                    "generate_record": True,
                },
            )
        )
