from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20))
    address = Column(Text)
    manager = Column(String(50))
    status = Column(String(20), default="active")
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    locations = relationship("StorageLocation", back_populates="warehouse")
    inventory_ledgers = relationship("InventoryLedger", back_populates="warehouse")


class StorageLocation(Base):
    __tablename__ = "storage_locations"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(100))
    max_capacity = Column(Numeric(18, 4))
    current_capacity = Column(Numeric(18, 4), default=0)
    status = Column(String(20), default="active")
    created_at = Column(DateTime)

    warehouse = relationship("Warehouse", back_populates="locations")
    inventory_ledgers = relationship("InventoryLedger", back_populates="location")


class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("storage_locations.id"))
    batch_no = Column(String(50))
    quantity = Column(Numeric(18, 4), default=0)
    available_quantity = Column(Numeric(18, 4), default=0)
    reserved_quantity = Column(Numeric(18, 4), default=0)
    unit = Column(String(20), default="个")
    in_date = Column(Date)
    expire_date = Column(Date)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    product = relationship("Product")
    warehouse = relationship("Warehouse", back_populates="inventory_ledgers")
    location = relationship("StorageLocation", back_populates="inventory_ledgers")
    transactions = relationship("InventoryTransaction", back_populates="ledger")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    ledger_id = Column(Integer, ForeignKey("inventory_ledger.id"))
    transaction_type = Column(String(20), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("storage_locations.id"))
    batch_no = Column(String(50))
    quantity = Column(Numeric(18, 4), nullable=False)
    before_quantity = Column(Numeric(18, 4))
    after_quantity = Column(Numeric(18, 4))
    unit_price = Column(Numeric(18, 4))
    total_amount = Column(Numeric(18, 2))
    reference_type = Column(String(50))
    reference_id = Column(Integer)
    transaction_date = Column(DateTime, nullable=False)
    operator = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime)

    ledger = relationship("InventoryLedger", back_populates="transactions")
    product = relationship("Product")
    warehouse = relationship("Warehouse")
    location = relationship("StorageLocation")
