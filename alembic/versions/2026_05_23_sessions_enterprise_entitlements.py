"""Add enterprise entitlement columns on sessions (market user + cached mod ids)

Revision ID: 2026_05_23_sessions_enterprise_entitlements
Revises: 2026_05_22_sessions_market_refresh_token
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa

revision = "2026_05_23_sessions_enterprise_entitlements"
down_revision = "2026_05_22_sessions_market_refresh_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("market_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("entitled_mod_ids_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("entitled_mod_ids_json")
        batch_op.drop_column("market_user_id")
