"""Add miniprogram tables for WeChat Mini Program CRM

Revision ID: xcagi_v5_miniprogram
Revises: xcagi_v4_inventory_purchase
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'xcagi_v5_miniprogram'
down_revision = 'xcagi_v4_inventory_purchase'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('wx_openid', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('wx_unionid', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('wx_avatar_url', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('mp_phone', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('mp_nickname', sa.String(length=64), nullable=True))

    op.create_index('ix_users_wx_openid', 'users', ['wx_openid'], unique=True)
    op.create_index('ix_users_wx_unionid', 'users', ['wx_unionid'])

    op.create_table(
        'mp_carts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('selected', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_mp_cart_user_product'),
    )
    op.create_index('ix_mp_carts_user_id', 'mp_carts', ['user_id'])

    op.create_table(
        'mp_orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_no', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('pay_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('pay_status', sa.String(length=20), server_default='unpaid'),
        sa.Column('pay_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_name', sa.String(length=64), nullable=True),
        sa.Column('delivery_phone', sa.String(length=20), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=True),
        sa.Column('delivery_province', sa.String(length=32), nullable=True),
        sa.Column('delivery_city', sa.String(length=32), nullable=True),
        sa.Column('delivery_district', sa.String(length=32), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_no'),
    )
    op.create_index('ix_mp_orders_order_no', 'mp_orders', ['order_no'])
    op.create_index('ix_mp_orders_user_id', 'mp_orders', ['user_id'])
    op.create_index('ix_mp_orders_status', 'mp_orders', ['status'])

    op.create_table(
        'mp_order_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(length=128), nullable=False),
        sa.Column('product_sku', sa.String(length=64), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['mp_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mp_order_items_order_id', 'mp_order_items', ['order_id'])

    op.create_table(
        'mp_addresses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('contact_name', sa.String(length=32), nullable=False),
        sa.Column('contact_phone', sa.String(length=20), nullable=False),
        sa.Column('province', sa.String(length=32), nullable=False),
        sa.Column('city', sa.String(length=32), nullable=False),
        sa.Column('district', sa.String(length=32), nullable=False),
        sa.Column('detail_address', sa.Text(), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mp_addresses_user_id', 'mp_addresses', ['user_id'])

    op.create_table(
        'mp_browse_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_mp_browse_user_product'),
    )
    op.create_index('ix_mp_browse_history_user_id', 'mp_browse_history', ['user_id'])

    op.create_table(
        'mp_favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_mp_fav_user_product'),
    )
    op.create_index('ix_mp_favorites_user_id', 'mp_favorites', ['user_id'])

    op.create_table(
        'mp_notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=32), server_default='system'),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('related_type', sa.String(length=32), nullable=True),
        sa.Column('related_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mp_notifications_user_id', 'mp_notifications', ['user_id'])

    op.create_table(
        'mp_feedbacks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('images', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending'),
        sa.Column('reply', sa.Text(), nullable=True),
        sa.Column('replied_by', sa.Integer(), nullable=True),
        sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['replied_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mp_feedbacks_user_id', 'mp_feedbacks', ['user_id'])


def downgrade():
    op.drop_table('mp_feedbacks')
    op.drop_table('mp_notifications')
    op.drop_table('mp_favorites')
    op.drop_table('mp_browse_history')
    op.drop_table('mp_addresses')
    op.drop_table('mp_order_items')
    op.drop_table('mp_orders')
    op.drop_table('mp_carts')

    op.drop_index('ix_users_wx_unionid', table_name='users')
    op.drop_index('ix_users_wx_openid', table_name='users')
    op.drop_column('users', 'mp_nickname')
    op.drop_column('users', 'mp_phone')
    op.drop_column('users', 'wx_avatar_url')
    op.drop_column('users', 'wx_unionid')
    op.drop_column('users', 'wx_openid')
