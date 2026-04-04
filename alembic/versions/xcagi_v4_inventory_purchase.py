"""Add inventory and purchase tables

Revision ID: xcagi_v4_inventory_purchase
Revises:
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa


revision = 'xcagi_v4_inventory_purchase'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'warehouses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('manager', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'storage_locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('max_capacity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('current_capacity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'inventory_ledger',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('batch_no', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('available_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('reserved_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('in_date', sa.Date(), nullable=True),
        sa.Column('expire_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.ForeignKeyConstraint(['location_id'], ['storage_locations.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'inventory_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ledger_id', sa.Integer(), nullable=True),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('batch_no', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('before_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('after_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(), nullable=False),
        sa.Column('operator', sa.String(length=50), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ledger_id'], ['inventory_ledger.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.ForeignKeyConstraint(['location_id'], ['storage_locations.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('contact_person', sa.String(length=50), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('contact_email', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('payment_terms', sa.String(length=50), nullable=True),
        sa.Column('credit_limit', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'purchase_orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_no', sa.String(length=50), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=True),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('delivery_date', sa.Date(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('paid_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('approver', sa.String(length=50), nullable=True),
        sa.Column('approve_date', sa.DateTime(), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_no')
    )

    op.create_table(
        'purchase_order_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(length=200), nullable=True),
        sa.Column('specification', sa.String(length=200), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('received_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('invoiced_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['purchase_orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'purchase_inbounds',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inbound_no', sa.String(length=50), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('inbound_date', sa.Date(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('handler', sa.String(length=50), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.ForeignKeyConstraint(['order_id'], ['purchase_orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('inbound_no')
    )

    op.create_table(
        'purchase_inbound_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inbound_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('order_item_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.String(length=200), nullable=True),
        sa.Column('batch_no', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['inbound_id'], ['purchase_inbounds.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['order_item_id'], ['purchase_order_items.id']),
        sa.ForeignKeyConstraint(['location_id'], ['storage_locations.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('purchase_inbound_items')
    op.drop_table('purchase_inbounds')
    op.drop_table('purchase_order_items')
    op.drop_table('purchase_orders')
    op.drop_table('suppliers')
    op.drop_table('inventory_transactions')
    op.drop_table('inventory_ledger')
    op.drop_table('storage_locations')
    op.drop_table('warehouses')
