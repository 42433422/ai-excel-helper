# -*- coding: utf-8 -*-
"""
小程序模块数据库模型
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MpCart(Base):
    __tablename__ = "mp_carts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    selected = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product")
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_mp_cart_user_product"),)


class MpOrder(Base):
    __tablename__ = "mp_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(20), nullable=False, default="pending")
    total_amount = Column(Numeric(12, 2), nullable=False)
    pay_amount = Column(Numeric(12, 2))
    pay_status = Column(String(20), default="unpaid")
    pay_time = Column(DateTime(timezone=True))

    delivery_name = Column(String(64))
    delivery_phone = Column(String(20))
    delivery_address = Column(Text)
    delivery_province = Column(String(32))
    delivery_city = Column(String(32))
    delivery_district = Column(String(32))

    remark = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    items = relationship(
        "MpOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="MpOrderItem.id",
    )


class MpOrderItem(Base):
    __tablename__ = "mp_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        Integer,
        ForeignKey("mp_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String(128), nullable=False)
    product_sku = Column(String(64))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    remark = Column(Text)

    order = relationship("MpOrder", back_populates="items")
    product = relationship("Product")


class MpAddress(Base):
    __tablename__ = "mp_addresses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_name = Column(String(32), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    province = Column(String(32), nullable=False)
    city = Column(String(32), nullable=False)
    district = Column(String(32), nullable=False)
    detail_address = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MpBrowseHistory(Base):
    __tablename__ = "mp_browse_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_mp_browse_user_product"),)


class MpFavorite(Base):
    __tablename__ = "mp_favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_mp_fav_user_product"),)


class MpNotification(Base):
    __tablename__ = "mp_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    content = Column(Text)
    type = Column(String(32), default="system")
    is_read = Column(Boolean, default=False)
    related_type = Column(String(32))
    related_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MpFeedback(Base):
    __tablename__ = "mp_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    images = Column(Text)
    status = Column(String(20), default="pending")
    reply = Column(Text)
    replied_by = Column(Integer, ForeignKey("users.id"))
    replied_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
