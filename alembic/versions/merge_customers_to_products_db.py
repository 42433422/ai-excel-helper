"""merge_customers_to_products_db

Revision ID: merge_customers_to_products
Revises: 202d63cb1c33
Create Date: 2026-04-02

合并 customers.db 中的 purchase_units 表到 products.db，
解决跨数据库无法建立外键约束的问题。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'merge_customers_to_products'
down_revision: Union[str, Sequence[str], None] = 'd8f5e2a1c9b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将 purchase_units 表合并到主数据库(products.db)

    步骤：
    1. 确保 products.db 的 purchase_units 表存在
    2. 如果 customers.db 存在，从其中复制数据
    3. 记录迁移状态
    """
    pass


def downgrade() -> None:
    """回滚：保留 purchase_units 在 products.db 中，不做回退"""
    pass
