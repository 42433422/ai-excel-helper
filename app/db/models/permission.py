from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from app.db.base import Base

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, default="")
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="joined"
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    description = Column(String, default="")
    module = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="joined"
    )


DEFAULT_PERMISSIONS = [
    {"name": "查看客户", "code": "customer.view", "module": "customer"},
    {"name": "编辑客户", "code": "customer.edit", "module": "customer"},
    {"name": "查看产品", "code": "product.view", "module": "product"},
    {"name": "编辑产品", "code": "product.edit", "module": "product"},
    {"name": "查看出货单", "code": "shipment.view", "module": "shipment"},
    {"name": "创建出货单", "code": "shipment.create", "module": "shipment"},
    {"name": "编辑出货单", "code": "shipment.edit", "module": "shipment"},
    {"name": "审批出货单", "code": "shipment.approve", "module": "shipment"},
    {"name": "标签打印", "code": "print.label", "module": "print"},
    {"name": "查看物料", "code": "material.view", "module": "material"},
    {"name": "编辑物料", "code": "material.edit", "module": "material"},
    {"name": "管理用户", "code": "admin.manage_users", "module": "admin"},
    {"name": "系统配置", "code": "admin.system_config", "module": "admin"},
]

DEFAULT_ROLES = [
    {
        "name": "viewer",
        "description": "只读用户",
        "permissions": [
            "customer.view", "product.view", "shipment.view", "material.view"
        ]
    },
    {
        "name": "operator",
        "description": "操作员",
        "permissions": [
            "customer.view", "customer.edit",
            "product.view", "product.edit",
            "shipment.view", "shipment.create", "shipment.edit",
            "material.view", "material.edit",
            "print.label"
        ]
    },
    {
        "name": "admin",
        "description": "管理员",
        "permissions": [
            "customer.view", "customer.edit",
            "product.view", "product.edit",
            "shipment.view", "shipment.create", "shipment.edit", "shipment.approve",
            "material.view", "material.edit",
            "print.label",
            "admin.manage_users", "admin.system_config"
        ]
    },
]
