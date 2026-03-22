"""add_rbac_tables

Revision ID: d8f5e2a1c9b3
Revises: ba97c759c51d
Create Date: 2026-03-21 10:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import User, Permission, Role, role_permissions as role_perm_table
from werkzeug.security import generate_password_hash


# revision identifiers, used by Alembic.
revision: str = 'd8f5e2a1c9b3'
down_revision: Union[str, Sequence[str], None] = '9e007d030e13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
        "permissions": ["customer.view", "product.view", "shipment.view", "material.view"]
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


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
    ), {"table_name": table_name})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=:index_name"
    ), {"index_name": index_name})
    return result.fetchone() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    columns = [row[1] for row in result.fetchall()]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, 'roles'):
        conn.execute(text("""
            CREATE TABLE roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL UNIQUE,
                description VARCHAR DEFAULT '',
                is_system BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    if not _table_exists(conn, 'permissions'):
        conn.execute(text("""
            CREATE TABLE permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL,
                code VARCHAR NOT NULL UNIQUE,
                description VARCHAR DEFAULT '',
                module VARCHAR DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    if not _table_exists(conn, 'role_permissions'):
        conn.execute(text("""
            CREATE TABLE role_permissions (
                role_id INTEGER NOT NULL,
                permission_id INTEGER NOT NULL,
                PRIMARY KEY (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            )
        """))

    if not _column_exists(conn, 'users', 'email'):
        conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR DEFAULT ''"))
    if not _column_exists(conn, 'users', 'is_active'):
        conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
    if not _column_exists(conn, 'users', 'created_by'):
        conn.execute(text("ALTER TABLE users ADD COLUMN created_by INTEGER REFERENCES users(id)"))

    if not _index_exists(conn, 'idx_users_is_active'):
        op.create_index('idx_users_is_active', 'users', ['is_active'])

    _seed_data(conn)


def _seed_data(conn):
    perm_map = {}
    for perm_data in DEFAULT_PERMISSIONS:
        result = conn.execute(text(
            "SELECT id FROM permissions WHERE code = :code"
        ), {"code": perm_data["code"]})
        row = result.fetchone()
        if row:
            perm_map[perm_data["code"]] = row[0]
        else:
            result = conn.execute(text(
                "INSERT INTO permissions (name, code, description, module) VALUES (:name, :code, :description, :module)"
            ), {"name": perm_data["name"], "code": perm_data["code"], "description": perm_data.get("description", ""), "module": perm_data["module"]})
            perm_map[perm_data["code"]] = result.lastrowid

    for role_data in DEFAULT_ROLES:
        result = conn.execute(text(
            "SELECT id FROM roles WHERE name = :name"
        ), {"name": role_data["name"]})
        row = result.fetchone()
        if row:
            role_id = row[0]
        else:
            result = conn.execute(text(
                "INSERT INTO roles (name, description, is_system) VALUES (:name, :description, 1)"
            ), {"name": role_data["name"], "description": role_data["description"]})
            role_id = result.lastrowid

        conn.execute(text("DELETE FROM role_permissions WHERE role_id = :role_id"), {"role_id": role_id})
        for perm_code in role_data["permissions"]:
            if perm_code in perm_map:
                conn.execute(text(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"
                ), {"role_id": role_id, "perm_id": perm_map[perm_code]})

    result = conn.execute(text("SELECT id FROM users WHERE username = 'admin'"))
    if not result.fetchone():
        conn.execute(text("""
            INSERT INTO users (username, password, display_name, email, role, is_active, created_at)
            VALUES ('admin', :password, '管理员', 'admin@local', 'admin', 1, :now)
        """), {"password": generate_password_hash("admin123"), "now": datetime.utcnow()})


def downgrade() -> None:
    conn = op.get_bind()
    op.drop_index('idx_users_is_active', 'users')
    if _table_exists(conn, 'role_permissions'):
        conn.execute(text("DROP TABLE IF EXISTS role_permissions"))
    if _table_exists(conn, 'permissions'):
        conn.execute(text("DROP TABLE IF EXISTS permissions"))
    if _table_exists(conn, 'roles'):
        conn.execute(text("DROP TABLE IF EXISTS roles"))
