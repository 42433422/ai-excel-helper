from app.db.models import PurchaseUnit as PurchaseUnitModel
from app.domain.customer.entities import Customer, PurchaseUnit
from app.domain.value_objects import ContactInfo


def purchase_unit_to_domain(db_model: PurchaseUnitModel) -> PurchaseUnit:
    return PurchaseUnit(
        id=db_model.id,
        unit_name=db_model.unit_name or "",
        contact_person=db_model.contact_person or "",
        contact_phone=db_model.contact_phone or "",
        address=db_model.address or "",
        discount_rate=db_model.discount_rate or 1.0,
        is_active=bool(db_model.is_active),
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def purchase_unit_to_db(unit: PurchaseUnit) -> dict:
    return {
        "unit_name": unit.unit_name,
        "contact_person": unit.contact_person,
        "contact_phone": unit.contact_phone,
        "address": unit.address,
        "discount_rate": unit.discount_rate,
        "is_active": 1 if unit.is_active else 0,
    }


def customer_to_domain(db_model: PurchaseUnitModel) -> Customer:
    return Customer(
        id=db_model.id,
        customer_name=db_model.unit_name or "",
        contact_info=ContactInfo(
            person=db_model.contact_person or "",
            phone=db_model.contact_phone or "",
            address=db_model.address or "",
        ),
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )
