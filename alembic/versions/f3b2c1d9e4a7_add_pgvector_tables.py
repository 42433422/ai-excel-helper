"""add_pgvector_tables

Revision ID: f3b2c1d9e4a7
Revises: d8f5e2a1c9b3
Create Date: 2026-03-27 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "f3b2c1d9e4a7"
down_revision: Union[str, Sequence[str], None] = "d8f5e2a1c9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS excel_vector_indexes (
                    index_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    created_at DOUBLE PRECISION NOT NULL,
                    updated_at DOUBLE PRECISION NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS excel_vector_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    index_id TEXT NOT NULL REFERENCES excel_vector_indexes(index_id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    embedding vector(256) NOT NULL,
                    metadata JSONB NOT NULL,
                    created_at DOUBLE PRECISION NOT NULL
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_excel_vector_chunks_index_id ON excel_vector_chunks(index_id)"))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_excel_vector_chunks_embedding ON excel_vector_chunks USING ivfflat (embedding vector_cosine_ops)"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(text("DROP TABLE IF EXISTS excel_vector_chunks"))
        conn.execute(text("DROP TABLE IF EXISTS excel_vector_indexes"))
