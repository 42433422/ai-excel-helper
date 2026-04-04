"""add_foreign_key_constraints_wechat

Revision ID: 66ee10160629
Revises: 8d4b53946b72
Create Date: 2026-03-20 20:22:11.667538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = '66ee10160629'
down_revision: Union[str, Sequence[str], None] = '8d4b53946b72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def upgrade() -> None:
    """Upgrade schema.
    
    添加以下外键约束：
    1. wechat_tasks.contact_id -> wechat_contacts.id (CASCADE)
    2. wechat_contact_context.contact_id -> wechat_contacts.id (CASCADE)
    """
    conn = op.get_bind()
    
    # 1. wechat_tasks.contact_id -> wechat_contacts.id
    if _table_exists(conn, 'wechat_tasks') and _table_exists(conn, 'wechat_contacts'):
        # 先清理孤儿记录
        conn.execute(text("""
            DELETE FROM wechat_tasks 
            WHERE contact_id IS NOT NULL 
            AND contact_id NOT IN (SELECT id FROM wechat_contacts)
        """))
        
        with op.batch_alter_table('wechat_tasks', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_wechat_tasks_contact_id_contacts',
                'wechat_contacts',
                ['contact_id'],
                ['id'],
                ondelete='CASCADE'
            )
    
    # 2. wechat_contact_context.contact_id -> wechat_contacts.id
    if _table_exists(conn, 'wechat_contact_context') and _table_exists(conn, 'wechat_contacts'):
        # 先清理孤儿记录
        conn.execute(text("""
            DELETE FROM wechat_contact_context 
            WHERE contact_id NOT IN (SELECT id FROM wechat_contacts)
        """))
        
        with op.batch_alter_table('wechat_contact_context', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_wechat_contact_context_contact_id_contacts',
                'wechat_contacts',
                ['contact_id'],
                ['id'],
                ondelete='CASCADE'
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    # 删除外键约束
    if _table_exists(conn, 'wechat_tasks'):
        with op.batch_alter_table('wechat_tasks', schema=None) as batch_op:
            batch_op.drop_constraint('fk_wechat_tasks_contact_id_contacts', type_='foreignkey')
    
    if _table_exists(conn, 'wechat_contact_context'):
        with op.batch_alter_table('wechat_contact_context', schema=None) as batch_op:
            batch_op.drop_constraint('fk_wechat_contact_context_contact_id_contacts', type_='foreignkey')
