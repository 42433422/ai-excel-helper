"""add_conversation_tables_pg

Revision ID: c4a9f8e1d2b3
Revises: b1f4a6d2e8c1
Create Date: 2026-03-27 03:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text


revision: str = "c4a9f8e1d2b3"
down_revision: Union[str, Sequence[str], None] = "b1f4a6d2e8c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if not _table_exists(conn, "ai_conversation_sessions"):
        conn.execute(
            text(
                """
                CREATE TABLE ai_conversation_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    session_id VARCHAR NOT NULL UNIQUE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR,
                    summary VARCHAR,
                    message_count INTEGER DEFAULT 0,
                    last_message_at TIMESTAMP,
                    created_at TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "ai_conversations"):
        conn.execute(
            text(
                """
                CREATE TABLE ai_conversations (
                    id BIGSERIAL PRIMARY KEY,
                    session_id VARCHAR NOT NULL REFERENCES ai_conversation_sessions(session_id) ON DELETE CASCADE,
                    user_id VARCHAR,
                    role VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    intent VARCHAR,
                    conversation_metadata TEXT,
                    created_at TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "user_preferences"):
        conn.execute(
            text(
                """
                CREATE TABLE user_preferences (
                    id BIGSERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    preference_key VARCHAR NOT NULL,
                    preference_value TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "user_memories"):
        conn.execute(
            text(
                """
                CREATE TABLE user_memories (
                    id BIGSERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    preferences TEXT,
                    frequent_actions TEXT,
                    historical_contexts TEXT,
                    feedback_history TEXT,
                    updated_at TIMESTAMP
                )
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    conn.execute(text("DROP TABLE IF EXISTS user_memories"))
    conn.execute(text("DROP TABLE IF EXISTS user_preferences"))
    conn.execute(text("DROP TABLE IF EXISTS ai_conversations"))
    conn.execute(text("DROP TABLE IF EXISTS ai_conversation_sessions"))
