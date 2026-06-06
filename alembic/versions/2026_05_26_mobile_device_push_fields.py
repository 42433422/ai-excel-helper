"""mobile_device_tokens: push_provider, push_token, product_sku."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "2026_05_26_mobile_device_push"
down_revision = "2026_05_23_sessions_enterprise_entitlements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("mobile_device_tokens")} if insp.has_table("mobile_device_tokens") else set()
    if not insp.has_table("mobile_device_tokens"):
        return
    if "push_provider" not in cols:
        op.add_column(
            "mobile_device_tokens",
            sa.Column("push_provider", sa.String(16), nullable=False, server_default="fcm"),
        )
    if "push_token" not in cols:
        op.add_column("mobile_device_tokens", sa.Column("push_token", sa.Text(), nullable=True))
        op.execute(sa.text("UPDATE mobile_device_tokens SET push_token = fcm_token WHERE push_token IS NULL"))
        op.alter_column("mobile_device_tokens", "push_token", nullable=False)
    if "product_sku" not in cols:
        op.add_column(
            "mobile_device_tokens",
            sa.Column("product_sku", sa.String(32), nullable=False, server_default="personal"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("mobile_device_tokens"):
        return
    cols = {c["name"] for c in insp.get_columns("mobile_device_tokens")}
    if "product_sku" in cols:
        op.drop_column("mobile_device_tokens", "product_sku")
    if "push_token" in cols:
        op.drop_column("mobile_device_tokens", "push_token")
    if "push_provider" in cols:
        op.drop_column("mobile_device_tokens", "push_provider")
