from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.base import Base


class PurchaseUnit(Base):
    __tablename__ = "purchase_units"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_name = Column(String, nullable=False)
    contact_person = Column(String)
    contact_phone = Column(String)
    address = Column(String)
    discount_rate = Column(Float, default=1.0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
