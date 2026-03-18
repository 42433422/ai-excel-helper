from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.db.base import Base


class ShipmentRecord(Base):
    __tablename__ = "shipment_records"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_unit = Column(String, nullable=False)
    unit_id = Column(Integer)
    product_name = Column(String, nullable=False)
    model_number = Column(String)
    quantity_kg = Column(Float, nullable=False)
    quantity_tins = Column(Integer, nullable=False)
    tin_spec = Column(Float)
    unit_price = Column(Float, default=0)
    amount = Column(Float, default=0)
    status = Column(String, default="pending")
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    printed_at = Column(DateTime)
    printer_name = Column(String)
    raw_text = Column(Text)
    parsed_data = Column(Text)
