# -*- coding: utf-8 -*-
"""
购买单位数据库模型（修复版）
映射到统一的 customer 数据库中的 purchase_units 表
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class PurchaseUnit(Base):
    """购买单位模型（修复版）"""
    __tablename__ = "purchase_units"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_name = Column(String(255), nullable=False, index=True)  # 购买单位名称
    contact_person = Column(String(100))  # 联系人
    contact_phone = Column(String(50))    # 联系电话
    address = Column(String(500))          # 地址
    is_active = Column(Boolean, default=True)  # 是否活跃
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Note: Relationship removed - cross-database relationships not supported in SQLite
    # ShipmentRecord is in a different database (products.db)
    
    def to_dict(self):
        """转换为字典格式，兼容前端客户列表"""
        return {
            "id": self.id,
            "customer_name": self.unit_name,  # 映射为 customer_name
            "contact_person": self.contact_person or "",
            "contact_phone": self.contact_phone or "",
            "contact_address": self.address or "",  # 映射为 contact_address
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# 创建别名类，保持向后兼容
Customer = PurchaseUnit