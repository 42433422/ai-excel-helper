"""Convert money-related Float columns to Numeric(10,2)

Revision ID: 2026_05_04_money_fields_float_to_numeric
Revises: xcagi_v5_approval_system
Create Date: 2026-05-04 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_05_04_money_fields_float_to_numeric"
down_revision = "xcagi_v5_approval_system"
branch_labels = None
depends_on = None


def upgrade():
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.alter_column(
            "unit_price",
            existing_type=sa.Float(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
            existing_server_default=None,
        )

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Float(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
            existing_server_default=None,
        )

    with op.batch_alter_table("shipment_records", schema=None) as batch_op:
        batch_op.alter_column(
            "unit_price",
            existing_type=sa.Float(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
            existing_server_default=None,
        )
        batch_op.alter_column(
            "amount",
            existing_type=sa.Float(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
            existing_server_default=None,
        )


def downgrade():
    # Revert Numeric back to Float (note: potential precision/scale loss)
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.alter_column(
            "unit_price",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Float(),
            existing_nullable=True,
            existing_server_default=None,
        )

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Float(),
            existing_nullable=True,
            existing_server_default=None,
        )

    with op.batch_alter_table("shipment_records", schema=None) as batch_op:
        batch_op.alter_column(
            "unit_price",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Float(),
            existing_nullable=True,
            existing_server_default=None,
        )
        batch_op.alter_column(
            "amount",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Float(),
            existing_nullable=True,
            existing_server_default=None,
        )

