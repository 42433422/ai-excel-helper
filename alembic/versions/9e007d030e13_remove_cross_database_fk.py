"""remove_cross_database_fk

Revision ID: 9e007d030e13
Revises: ba97c759c51d
Create Date: 2026-03-20 20:46:36.139121

说明：移除跨数据库的外键约束
SQLite 不支持跨数据库的外键约束，因为 shipment_records 在 products.db 中，
而 purchase_units 在 customers.db 中。

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '9e007d030e13'
down_revision: Union[str, Sequence[str], None] = 'ba97c759c51d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def upgrade() -> None:
    """Upgrade schema.
    
    移除 shipment_records.unit_id 的外键约束
    原因：跨数据库外键约束在 SQLite 中不受支持
    """
    conn = op.get_bind()
    
    # 检查外键是否存在并删除
    if _table_exists(conn, 'shipment_records'):
        # SQLite 中需要重建表来删除外键
        # 但这里我们只需要在模型中移除 ForeignKey 定义
        # 实际的外键约束在 batch_alter_table 中删除
        with op.batch_alter_table('shipment_records', schema=None) as batch_op:
            # 删除外键约束（如果存在）
            try:
                batch_op.drop_constraint('fk_shipment_records_unit_id_purchase_units', type_='foreignkey')
            except Exception:
                # 如果约束不存在，忽略错误
                pass


def downgrade() -> None:
    """Downgrade schema."""
    # 不恢复跨数据库外键
    pass
