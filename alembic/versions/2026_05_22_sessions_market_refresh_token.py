"""Add market_refresh_token to sessions for long-lived Xiuci market JWT refresh

Revision ID: 2026_05_22_sessions_market_refresh_token
Revises: 2026_05_10_seed_sunbird_demo_user
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa

revision = "2026_05_22_sessions_market_refresh_token"
down_revision = "2026_05_10_seed_sunbird_demo_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("market_refresh_token", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("market_refresh_token")
