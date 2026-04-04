"""bootstrap_core_business_tables_pg

Revision ID: b1f4a6d2e8c1
Revises: f3b2c1d9e4a7
Create Date: 2026-03-27 02:18:00.000000
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = "b1f4a6d2e8c1"
down_revision: Union[str, Sequence[str], None] = "f3b2c1d9e4a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    if not is_pg:
        return

    if not _table_exists(conn, "purchase_units"):
        conn.execute(
            text(
                """
                CREATE TABLE purchase_units (
                    id BIGSERIAL PRIMARY KEY,
                    unit_name VARCHAR(255) NOT NULL,
                    contact_person VARCHAR(100),
                    contact_phone VARCHAR(50),
                    address VARCHAR(500),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "products"):
        conn.execute(
            text(
                """
                CREATE TABLE products (
                    id BIGSERIAL PRIMARY KEY,
                    model_number VARCHAR,
                    name VARCHAR NOT NULL,
                    specification VARCHAR,
                    price DOUBLE PRECISION DEFAULT 0,
                    quantity INTEGER,
                    description VARCHAR,
                    category VARCHAR,
                    brand VARCHAR,
                    unit VARCHAR DEFAULT '个',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "shipment_records"):
        conn.execute(
            text(
                """
                CREATE TABLE shipment_records (
                    id BIGSERIAL PRIMARY KEY,
                    purchase_unit VARCHAR NOT NULL,
                    unit_id INTEGER,
                    product_name VARCHAR NOT NULL,
                    model_number VARCHAR,
                    quantity_kg DOUBLE PRECISION NOT NULL,
                    quantity_tins INTEGER NOT NULL,
                    tin_spec DOUBLE PRECISION,
                    unit_price DOUBLE PRECISION DEFAULT 0,
                    amount DOUBLE PRECISION DEFAULT 0,
                    status VARCHAR DEFAULT 'pending',
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    printed_at TIMESTAMP,
                    printer_name VARCHAR,
                    raw_text TEXT,
                    parsed_data TEXT
                )
                """
            )
        )

    if not _table_exists(conn, "wechat_contacts"):
        conn.execute(
            text(
                """
                CREATE TABLE wechat_contacts (
                    id BIGSERIAL PRIMARY KEY,
                    contact_name VARCHAR NOT NULL,
                    remark VARCHAR,
                    wechat_id VARCHAR,
                    contact_type VARCHAR DEFAULT 'contact',
                    is_active INTEGER DEFAULT 1,
                    is_starred INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "wechat_tasks"):
        conn.execute(
            text(
                """
                CREATE TABLE wechat_tasks (
                    id BIGSERIAL PRIMARY KEY,
                    contact_id INTEGER REFERENCES wechat_contacts(id) ON DELETE CASCADE,
                    username VARCHAR,
                    display_name VARCHAR,
                    message_id VARCHAR,
                    msg_timestamp INTEGER,
                    raw_text TEXT NOT NULL,
                    task_type VARCHAR DEFAULT 'unknown',
                    status VARCHAR DEFAULT 'pending',
                    last_status_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "wechat_contact_context"):
        conn.execute(
            text(
                """
                CREATE TABLE wechat_contact_context (
                    id BIGSERIAL PRIMARY KEY,
                    contact_id INTEGER NOT NULL REFERENCES wechat_contacts(id) ON DELETE CASCADE,
                    wechat_id VARCHAR,
                    context_json TEXT,
                    message_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

    if not _table_exists(conn, "distillation_log"):
        conn.execute(
            text(
                """
                CREATE TABLE distillation_log (
                    id BIGSERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    slots TEXT,
                    confidence DOUBLE PRECISION DEFAULT 1.0,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_for_training INTEGER DEFAULT 0
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_intent ON distillation_log(intent)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_used ON distillation_log(used_for_training)"))

    if not _table_exists(conn, "training_stats"):
        conn.execute(
            text(
                """
                CREATE TABLE training_stats (
                    id BIGSERIAL PRIMARY KEY,
                    intent TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    conn.execute(text("DROP TABLE IF EXISTS training_stats"))
    conn.execute(text("DROP TABLE IF EXISTS distillation_log"))
    conn.execute(text("DROP TABLE IF EXISTS wechat_contact_context"))
    conn.execute(text("DROP TABLE IF EXISTS wechat_tasks"))
    conn.execute(text("DROP TABLE IF EXISTS wechat_contacts"))
    conn.execute(text("DROP TABLE IF EXISTS shipment_records"))
    conn.execute(text("DROP TABLE IF EXISTS products"))
    conn.execute(text("DROP TABLE IF EXISTS purchase_units"))
