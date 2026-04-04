from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(50))
    contact_phone = Column(String(50))
    contact_email = Column(String(100))
    address = Column(Text)
    payment_terms = Column(String(50))
    credit_limit = Column(Numeric(18, 2), default=0)
    status = Column(String(20), default="active")
    rating = Column(Integer, default=3)
    remark = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    order_date = Column(Date, nullable=False)
    delivery_date = Column(Date)
    total_amount = Column(Numeric(18, 2), default=0)
    paid_amount = Column(Numeric(18, 2), default=0)
    status = Column(String(20), default="draft")
    approver = Column(String(50))
    approve_date = Column(DateTime)
    remark = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    warehouse = relationship("Warehouse")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200))
    specification = Column(String(200))
    quantity = Column(Numeric(18, 4), nullable=False)
    unit = Column(String(20), default="个")
    unit_price = Column(Numeric(18, 4), default=0)
    amount = Column(Numeric(18, 2), default=0)
    received_quantity = Column(Numeric(18, 4), default=0)
    invoiced_quantity = Column(Numeric(18, 4), default=0)
    status = Column(String(20), default="pending")
    remark = Column(Text)
    created_at = Column(DateTime)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")


class PurchaseInbound(Base):
    __tablename__ = "purchase_inbounds"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    inbound_no = Column(String(50), unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    inbound_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(18, 2), default=0)
    status = Column(String(20), default="draft")
    handler = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")
    purchase_order = relationship("PurchaseOrder")
    items = relationship("PurchaseInboundItem", back_populates="inbound", cascade="all, delete-orphan")


class PurchaseInboundItem(Base):
    __tablename__ = "purchase_inbound_items"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    inbound_id = Column(Integer, ForeignKey("purchase_inbounds.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("purchase_order_items.id"))
    product_name = Column(String(200))
    batch_no = Column(String(50))
    quantity = Column(Numeric(18, 4), nullable=False)
    unit = Column(String(20), default="个")
    unit_price = Column(Numeric(18, 4), default=0)
    amount = Column(Numeric(18, 2), default=0)
    location_id = Column(Integer, ForeignKey("storage_locations.id"))
    remark = Column(Text)
    created_at = Column(DateTime)

    inbound = relationship("PurchaseInbound", back_populates="items")
    product = relationship("Product")
    order_item = relationship("PurchaseOrderItem")
    location = relationship("StorageLocation")
