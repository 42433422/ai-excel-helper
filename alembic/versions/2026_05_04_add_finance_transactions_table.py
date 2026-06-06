"""Add financial_transactions table for finance module

Revision ID: 2026_05_04_add_finance_transactions
Revises: 2026_05_04_money_fields_float_to_numeric
Create Date: 2026-05-04 22:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "2026_05_04_add_finance_transactions"
down_revision = "2026_05_04_money_fields_float_to_numeric"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="CNY"),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("counterparty_name", sa.String(length=128), nullable=True),
        sa.Column("counterparty_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_financial_transactions_transaction_type",
        "financial_transactions",
        ["transaction_type"],
    )
    op.create_index(
        "ix_financial_transactions_transaction_date",
        "financial_transactions",
        ["transaction_date"],
    )
    op.create_index(
        "ix_financial_transactions_status",
        "financial_transactions",
        ["status"],
    )
    op.create_index(
        "ix_financial_transactions_reference_id",
        "financial_transactions",
        ["reference_id"],
    )
    op.create_index(
        "ix_fin_txn_type_date",
        "financial_transactions",
        ["transaction_type", "transaction_date"],
    )
    op.create_index(
        "ix_fin_txn_ref",
        "financial_transactions",
        ["reference_type", "reference_id"],
    )


def downgrade():
    op.drop_index("ix_fin_txn_ref", table_name="financial_transactions")
    op.drop_index("ix_fin_txn_type_date", table_name="financial_transactions")
    op.drop_index("ix_financial_transactions_reference_id", table_name="financial_transactions")
    op.drop_index("ix_financial_transactions_status", table_name="financial_transactions")
    op.drop_index("ix_financial_transactions_transaction_date", table_name="financial_transactions")
    op.drop_index("ix_financial_transactions_transaction_type", table_name="financial_transactions")
    op.drop_table("financial_transactions")
