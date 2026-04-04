from datetime import datetime
from typing import List, Optional

from app.db.models import PurchaseUnit as PurchaseUnitModel
from app.db.session import get_db
from app.domain.customer.entities import Customer, PurchaseUnit
from app.domain.value_objects import ContactInfo
from app.infrastructure.repositories.customer_repository import CustomerRepository


class SQLAlchemyCustomerRepository(CustomerRepository):
    """客户仓储 SQLAlchemy 实现 - 使用 products.db（已合并 purchase_units 表）"""

    def _to_unit_domain(self, db_model: PurchaseUnitModel) -> PurchaseUnit:
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

    def _to_unit_db(self, unit: PurchaseUnit) -> dict:
        return {
            "unit_name": unit.unit_name,
            "contact_person": unit.contact_person,
            "contact_phone": unit.contact_phone,
            "address": unit.address,
            "discount_rate": unit.discount_rate,
            "is_active": 1 if unit.is_active else 0,
        }

    def save_customer(self, customer: Customer) -> Customer:
        with get_db() as db:
            existing = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.unit_name == customer.customer_name).first()
            if existing:
                existing.contact_person = customer.contact_info.person
                existing.contact_phone = customer.contact_info.phone
                existing.address = customer.contact_info.address
                existing.updated_at = datetime.now()
                db.commit()
                db.refresh(existing)
                return self._to_unit_domain(existing)
            unit = PurchaseUnitModel(
                unit_name=customer.customer_name,
                contact_person=customer.contact_info.person,
                contact_phone=customer.contact_info.phone,
                address=customer.contact_info.address,
            )
            db.add(unit)
            db.commit()
            db.refresh(unit)
            return self._to_unit_domain(unit)

    def find_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        with get_db() as db:
            model = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == customer_id).first()
            if not model:
                return None
            return Customer(
                id=model.id,
                customer_name=model.unit_name or "",
                contact_info=ContactInfo(
                    person=model.contact_person or "",
                    phone=model.contact_phone or "",
                    address=model.address or ""
                ),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

    def find_customer_by_name(self, name: str) -> Optional[Customer]:
        with get_db() as db:
            model = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.unit_name == name).first()
            if not model:
                return None
            return Customer(
                id=model.id,
                customer_name=model.unit_name or "",
                contact_info=ContactInfo(
                    person=model.contact_person or "",
                    phone=model.contact_phone or "",
                    address=model.address or ""
                ),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

    def find_all_customers(self) -> List[Customer]:
        with get_db() as db:
            models = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.is_active == True).all()
            return [
                Customer(
                    id=m.id,
                    customer_name=m.unit_name or "",
                    contact_info=ContactInfo(
                        person=m.contact_person or "",
                        phone=m.contact_phone or "",
                        address=m.address or ""
                    ),
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in models
            ]

    def delete_customer(self, customer_id: int) -> bool:
        with get_db() as db:
            model = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == customer_id).first()
            if model:
                db.delete(model)
                db.commit()
                return True
            return False

    def save_purchase_unit(self, unit: PurchaseUnit) -> PurchaseUnit:
        with get_db() as db:
            if unit.id:
                existing = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == unit.id).first()
                if existing:
                    for key, value in self._to_unit_db(unit).items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.now()
                    db.commit()
                    db.refresh(existing)
                    return self._to_unit_domain(existing)

            db_model = PurchaseUnitModel(**self._to_unit_db(unit))
            db.add(db_model)
            db.commit()
            db.refresh(db_model)
            unit.id = db_model.id
            return unit

    def find_purchase_unit_by_id(self, unit_id: int) -> Optional[PurchaseUnit]:
        with get_db() as db:
            model = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == unit_id).first()
            return self._to_unit_domain(model) if model else None

    def find_purchase_unit_by_name(self, name: str) -> Optional[PurchaseUnit]:
        with get_db() as db:
            model = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.unit_name == name).first()
            return self._to_unit_domain(model) if model else None

    def find_all_purchase_units(self) -> List[PurchaseUnit]:
        with get_db() as db:
            models = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.is_active == 1).all()
            return [self._to_unit_domain(m) for m in models]

    def delete_purchase_unit(self, unit_id: int) -> bool:
        with get_db() as db:
            model = db.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == unit_id).first()
            if model:
                db.delete(model)
                db.commit()
                return True
            return False
