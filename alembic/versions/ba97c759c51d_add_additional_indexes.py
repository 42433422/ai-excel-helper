"""add_additional_indexes

Revision ID: ba97c759c51d
Revises: 0ca9c7759440
Create Date: 2026-03-20 20:22:13.341435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'ba97c759c51d'
down_revision: Union[str, Sequence[str], None] = '0ca9c7759440'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    """检查表是否存在"""
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
    ), {"table_name": table_name})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    """检查索引是否存在"""
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=:index_name"
    ), {"index_name": index_name})
    return result.fetchone() is not None


def upgrade() -> None:
    """Upgrade schema.
    
    添加以下索引：
    1. shipment_records(status, created_at) - 按状态查询
    2. ai_conversations(session_id, created_at) - 会话对话查询
    3. products(category, is_active) - 产品分类查询
    4. wechat_tasks(status, updated_at) - 任务状态更新查询
    5. sessions(expires_at) - 会话过期清理
    """
    conn = op.get_bind()
    
    # 1. shipment_records(status, created_at)
    if _table_exists(conn, 'shipment_records'):
        if not _index_exists(conn, 'idx_shipment_records_status_date'):
            conn.execute(text("""
                CREATE INDEX idx_shipment_records_status_date 
                ON shipment_records(status, created_at)
            """))
    
    # 2. ai_conversations(session_id, created_at)
    if _table_exists(conn, 'ai_conversations'):
        if not _index_exists(conn, 'idx_ai_conversations_session_date'):
            conn.execute(text("""
                CREATE INDEX idx_ai_conversations_session_date 
                ON ai_conversations(session_id, created_at)
            """))
    
    # 3. products(category, is_active)
    if _table_exists(conn, 'products'):
        if not _index_exists(conn, 'idx_products_category_active'):
            conn.execute(text("""
                CREATE INDEX idx_products_category_active 
                ON products(category, is_active)
            """))
    
    # 4. wechat_tasks(status, updated_at)
    if _table_exists(conn, 'wechat_tasks'):
        if not _index_exists(conn, 'idx_wechat_tasks_status_updated'):
            conn.execute(text("""
                CREATE INDEX idx_wechat_tasks_status_updated 
                ON wechat_tasks(status, updated_at)
            """))
    
    # 5. sessions(expires_at)
    if _table_exists(conn, 'sessions'):
        if not _index_exists(conn, 'idx_sessions_expires'):
            conn.execute(text("""
                CREATE INDEX idx_sessions_expires 
                ON sessions(expires_at)
            """))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    # 删除索引
    indexes_to_drop = [
        'idx_shipment_records_status_date',
        'idx_ai_conversations_session_date',
        'idx_products_category_active',
        'idx_wechat_tasks_status_updated',
        'idx_sessions_expires'
    ]
    
    for index_name in indexes_to_drop:
        if _index_exists(conn, index_name):
            conn.execute(text(f"DROP INDEX {index_name}"))
