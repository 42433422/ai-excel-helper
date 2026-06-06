from typing import Any

from app.db.models import ShipmentRecord
from app.domain.shipment.aggregates import Shipment
from app.domain.value_objects import ContactInfo, OrderNumber


def shipment_to_domain(db_record: ShipmentRecord) -> Shipment:
    return Shipment(
        id=db_record.id,
        order_number=OrderNumber(str(db_record.id)),
        purchase_unit_name=db_record.purchase_unit or "",
        contact_info=ContactInfo.empty(),
        status=db_record.status or "pending",
        created_at=db_record.created_at,
        updated_at=db_record.updated_at,
        printed_at=db_record.printed_at,
        printer_name=db_record.printer_name,
        raw_text=db_record.raw_text,
    )


def shipment_to_db(shipment: Shipment) -> dict[str, Any]:
    # Note: This mirrors previous repository logic. Mapping of items and totals
    # should be expanded if the DB schema stores separate line items.
    return {
        "purchase_unit": shipment.purchase_unit_name,
        "product_name": shipment.items[0].product_name if shipment.items else "",
        "model_number": shipment.items[0].model_number if shipment.items else "",
        "quantity_kg": shipment.total_quantity.kg,
        "quantity_tins": shipment.total_quantity.tins,
        "tin_spec": shipment.total_quantity.spec_per_tin,
        "unit_price": (
            shipment.total_amount.amount / shipment.total_quantity.kg
            if shipment.total_quantity.kg
            else 0
        ),
        "amount": shipment.total_amount.amount,
        "status": shipment.status,
        "created_at": shipment.created_at,
        "updated_at": shipment.updated_at,
        "printed_at": shipment.printed_at,
        "printer_name": shipment.printer_name,
        "raw_text": shipment.raw_text,
    }
