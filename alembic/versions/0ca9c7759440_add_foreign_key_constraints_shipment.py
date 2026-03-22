"""add_foreign_key_constraints_shipment

Revision ID: 0ca9c7759440
Revises: 66ee10160629
Create Date: 2026-03-20 20:22:12.664811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0ca9c7759440'
down_revision: Union[str, Sequence[str], None] = '66ee10160629'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    """检查表是否存在"""
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
    ), {"table_name": table_name})
    return result.fetchone() is not None


def upgrade() -> None:
    """Upgrade schema.
    
    添加外键约束：
    1. shipment_records.unit_id -> purchase_units.id (SET NULL)
    """
    conn = op.get_bind()
    
    # shipment_records.unit_id -> purchase_units.id
    if _table_exists(conn, 'shipment_records') and _table_exists(conn, 'purchase_units'):
        # 先清理孤儿记录（将无效的 unit_id 设为 NULL）
        conn.execute(text("""
            UPDATE shipment_records 
            SET unit_id = NULL 
            WHERE unit_id IS NOT NULL 
            AND unit_id NOT IN (SELECT id FROM purchase_units)
        """))
        
        with op.batch_alter_table('shipment_records', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_shipment_records_unit_id_purchase_units',
                'purchase_units',
                ['unit_id'],
                ['id'],
                ondelete='SET NULL'
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    # 删除外键约束
    if _table_exists(conn, 'shipment_records'):
        with op.batch_alter_table('shipment_records', schema=None) as batch_op:
            batch_op.drop_constraint('fk_shipment_records_unit_id_purchase_units', type_='foreignkey')
