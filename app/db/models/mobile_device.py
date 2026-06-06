"""移动端 FCM / 设备令牌（Android）。"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.db.base import Base
from app.utils.time import utc_now_naive


class MobileDeviceToken(Base):
    __tablename__ = "mobile_device_tokens"
    __table_args__ = (UniqueConstraint("user_id", "fcm_token", name="uq_mobile_device_user_token"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    fcm_token = Column(Text, nullable=False)
    push_provider = Column(String(16), nullable=False, default="fcm")
    push_token = Column(Text, nullable=False, default="")
    product_sku = Column(String(32), nullable=False, default="personal")
    platform = Column(String(32), nullable=False, default="android")
    device_label = Column(String(200), nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=utc_now_naive, onupdate=utc_now_naive)
