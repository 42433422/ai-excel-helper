from datetime import datetime
from typing import List, Optional

from app.application.customer_app_service import get_customers_session
from app.db.models import PurchaseUnit as PurchaseUnitModel
from app.domain.customer.entities import Customer, PurchaseUnit
from app.domain.value_objects import ContactInfo
from app.infrastructure.repositories.customer_repository import CustomerRepository


class SQLAlchemyCustomerRepository(CustomerRepository):
    """客户仓储 SQLAlchemy 实现 - 使用 customers.db"""

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
        session = get_customers_session()
        try:
            existing = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.unit_name == customer.customer_name).first()
            if existing:
                existing.contact_person = customer.contact_info.person
                existing.contact_phone = customer.contact_info.phone
                existing.address = customer.contact_info.address
                existing.updated_at = datetime.now()
                session.commit()
                session.refresh(existing)
                return self._to_unit_domain(existing)
            unit = PurchaseUnitModel(
                unit_name=customer.customer_name,
                contact_person=customer.contact_info.person,
                contact_phone=customer.contact_info.phone,
                address=customer.contact_info.address,
            )
            session.add(unit)
            session.commit()
            session.refresh(unit)
            return self._to_unit_domain(unit)
        finally:
            session.close()

    def find_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        session = get_customers_session()
        try:
            model = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == customer_id).first()
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
        finally:
            session.close()

    def find_customer_by_name(self, name: str) -> Optional[Customer]:
        session = get_customers_session()
        try:
            model = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.unit_name == name).first()
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
        finally:
            session.close()

    def find_all_customers(self) -> List[Customer]:
        session = get_customers_session()
        try:
            models = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.is_active == True).all()
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
        finally:
            session.close()

    def delete_customer(self, customer_id: int) -> bool:
        session = get_customers_session()
        try:
            model = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == customer_id).first()
            if model:
                session.delete(model)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def save_purchase_unit(self, unit: PurchaseUnit) -> PurchaseUnit:
        session = get_customers_session()
        try:
            if unit.id:
                existing = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == unit.id).first()
                if existing:
                    for key, value in self._to_unit_db(unit).items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.now()
                    session.commit()
                    session.refresh(existing)
                    return self._to_unit_domain(existing)

            db_model = PurchaseUnitModel(**self._to_unit_db(unit))
            session.add(db_model)
            session.commit()
            session.refresh(db_model)
            unit.id = db_model.id
            return unit
        finally:
            session.close()

    def find_purchase_unit_by_id(self, unit_id: int) -> Optional[PurchaseUnit]:
        session = get_customers_session()
        try:
            model = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == unit_id).first()
            return self._to_unit_domain(model) if model else None
        finally:
            session.close()

    def find_purchase_unit_by_name(self, name: str) -> Optional[PurchaseUnit]:
        session = get_customers_session()
        try:
            model = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.unit_name == name).first()
            return self._to_unit_domain(model) if model else None
        finally:
            session.close()

    def find_all_purchase_units(self) -> List[PurchaseUnit]:
        session = get_customers_session()
        try:
            models = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.is_active == 1).all()
            return [self._to_unit_domain(m) for m in models]
        finally:
            session.close()

    def delete_purchase_unit(self, unit_id: int) -> bool:
        session = get_customers_session()
        try:
            model = session.query(PurchaseUnitModel).filter(PurchaseUnitModel.id == unit_id).first()
            if model:
                session.delete(model)
                session.commit()
                return True
            return False
        finally:
            session.close()
