"""Add market_access_token to sessions for修茈 JWT handoff across workers

Revision ID: 2026_05_10_sessions_market_access_token
Revises: 2026_05_04_add_finance_transactions
Create Date: 2026-05-10
"""
import sqlalchemy as sa
from alembic import op

revision = "2026_05_10_sessions_market_access_token"
down_revision = "2026_05_04_add_finance_transactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("market_access_token", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("market_access_token")
