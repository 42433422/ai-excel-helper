"""add_recommended_indexes

Revision ID: a7d310349a7d
Revises: 202d63cb1c33
Create Date: 2026-03-17 01:24:14.577578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = 'a7d310349a7d'
down_revision: Union[str, Sequence[str], None] = '202d63cb1c33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    
    if _table_exists(conn, 'shipment_records'):
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shipment_records_unit_date 
            ON shipment_records(purchase_unit, created_at)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shipment_records_created 
            ON shipment_records(created_at)
        """))
    
    if _table_exists(conn, 'purchase_units'):
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_purchase_units_name_active 
            ON purchase_units(unit_name, is_active)
        """))
    
    if _table_exists(conn, 'products'):
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_products_model 
            ON products(model_number)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_products_name 
            ON products(name)
        """))
    
    if _table_exists(conn, 'wechat_contacts'):
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_wechat_contacts_type_active 
            ON wechat_contacts(contact_type, is_active)
        """))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    def _index_exists(index_name: str) -> bool:
        all_indexes = []
        for table_name in inspect(conn).get_table_names():
            all_indexes.extend([idx.get("name") for idx in inspect(conn).get_indexes(table_name)])
        return index_name in all_indexes
    
    if _index_exists('idx_wechat_contacts_type_active'):
        conn.execute(text("DROP INDEX idx_wechat_contacts_type_active"))
    if _index_exists('idx_products_name'):
        conn.execute(text("DROP INDEX idx_products_name"))
    if _index_exists('idx_products_model'):
        conn.execute(text("DROP INDEX idx_products_model"))
    if _index_exists('idx_purchase_units_name_active'):
        conn.execute(text("DROP INDEX idx_purchase_units_name_active"))
    if _index_exists('idx_shipment_records_created'):
        conn.execute(text("DROP INDEX idx_shipment_records_created"))
    if _index_exists('idx_shipment_records_unit_date'):
        conn.execute(text("DROP INDEX idx_shipment_records_unit_date"))
