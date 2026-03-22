"""add_foreign_key_constraints_sessions_and_ai

Revision ID: 8d4b53946b72
Revises: a7d310349a7d
Create Date: 2026-03-20 20:22:03.947176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '8d4b53946b72'
down_revision: Union[str, Sequence[str], None] = 'a7d310349a7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    """检查表是否存在"""
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
    ), {"table_name": table_name})
    return result.fetchone() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    result = conn.execute(text(
        f"PRAGMA table_info({table_name})"
    ))
    for row in result.fetchall():
        if row[1] == column_name:
            return True
    return False


def upgrade() -> None:
    """Upgrade schema.
    
    添加以下外键约束：
    1. sessions.user_id -> users.id (CASCADE)
    2. ai_conversation_sessions.user_id -> users.id (CASCADE)
    3. ai_conversations.session_id -> ai_conversation_sessions.session_id (CASCADE)
    4. ai_tools.category_id -> ai_tool_categories.id (SET NULL)
    """
    conn = op.get_bind()
    
    # 1. sessions.user_id -> users.id
    if _table_exists(conn, 'sessions') and _table_exists(conn, 'users'):
        # 先清理孤儿记录
        conn.execute(text("""
            DELETE FROM sessions 
            WHERE user_id NOT IN (SELECT id FROM users)
        """))
        
        # SQLite 中添加外键需要重建表
        with op.batch_alter_table('sessions', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_sessions_user_id_users',
                'users',
                ['user_id'],
                ['id'],
                ondelete='CASCADE'
            )
    
    # 2. ai_conversation_sessions.user_id -> users.id
    if _table_exists(conn, 'ai_conversation_sessions') and _table_exists(conn, 'users'):
        # 先清理孤儿记录
        conn.execute(text("""
            DELETE FROM ai_conversation_sessions 
            WHERE user_id NOT IN (SELECT id FROM users)
        """))
        
        with op.batch_alter_table('ai_conversation_sessions', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_ai_conversation_sessions_user_id_users',
                'users',
                ['user_id'],
                ['id'],
                ondelete='CASCADE'
            )
    
    # 3. ai_conversations.session_id -> ai_conversation_sessions.session_id
    if _table_exists(conn, 'ai_conversations') and _table_exists(conn, 'ai_conversation_sessions'):
        # 先清理孤儿记录
        conn.execute(text("""
            DELETE FROM ai_conversations 
            WHERE session_id NOT IN (SELECT session_id FROM ai_conversation_sessions)
        """))
        
        with op.batch_alter_table('ai_conversations', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_ai_conversations_session_id_sessions',
                'ai_conversation_sessions',
                ['session_id'],
                ['session_id'],
                ondelete='CASCADE'
            )
    
    # 4. ai_tools.category_id -> ai_tool_categories.id
    if _table_exists(conn, 'ai_tools') and _table_exists(conn, 'ai_tool_categories'):
        # 先清理孤儿记录（将无效的 category_id 设为 NULL）
        conn.execute(text("""
            UPDATE ai_tools 
            SET category_id = NULL 
            WHERE category_id NOT IN (SELECT id FROM ai_tool_categories)
        """))
        
        with op.batch_alter_table('ai_tools', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_ai_tools_category_id_categories',
                'ai_tool_categories',
                ['category_id'],
                ['id'],
                ondelete='SET NULL'
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    # 删除外键约束（SQLite 中需要重建表）
    if _table_exists(conn, 'sessions'):
        with op.batch_alter_table('sessions', schema=None) as batch_op:
            batch_op.drop_constraint('fk_sessions_user_id_users', type_='foreignkey')
    
    if _table_exists(conn, 'ai_conversation_sessions'):
        with op.batch_alter_table('ai_conversation_sessions', schema=None) as batch_op:
            batch_op.drop_constraint('fk_ai_conversation_sessions_user_id_users', type_='foreignkey')
    
    if _table_exists(conn, 'ai_conversations'):
        with op.batch_alter_table('ai_conversations', schema=None) as batch_op:
            batch_op.drop_constraint('fk_ai_conversations_session_id_sessions', type_='foreignkey')
    
    if _table_exists(conn, 'ai_tools'):
        with op.batch_alter_table('ai_tools', schema=None) as batch_op:
            batch_op.drop_constraint('fk_ai_tools_category_id_categories', type_='foreignkey')
