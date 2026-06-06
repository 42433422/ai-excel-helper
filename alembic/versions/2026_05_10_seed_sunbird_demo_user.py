"""Seed demo user SUNBIRD for 太阳鸟 pro login parity with docs/screenshots.

Revision ID: 2026_05_10_seed_sunbird_demo_user
Revises: 2026_05_10_sessions_market_access_token
Create Date: 2026-05-10
"""

from alembic import op
from sqlalchemy import text

from app.utils.password_hash import generate_password_hash
from app.utils.time import utc_now_naive

revision = "2026_05_10_seed_sunbird_demo_user"
down_revision = "2026_05_10_sessions_market_access_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"
    row = conn.execute(text("SELECT id FROM users WHERE username = 'SUNBIRD'")).fetchone()
    if row:
        return

    password = generate_password_hash("SUN123456")
    now = utc_now_naive()
    if is_pg:
        conn.execute(
            text(
                """
                INSERT INTO users (username, password, display_name, email, role, is_active, created_at)
                VALUES ('SUNBIRD', :password, '太阳鸟演示', 'sunbird@local', 'admin', TRUE, :now)
                """
            ),
            {"password": password, "now": now},
        )
    else:
        conn.execute(
            text(
                """
                INSERT INTO users (username, password, display_name, email, role, is_active, created_at)
                VALUES ('SUNBIRD', :password, '太阳鸟演示', 'sunbird@local', 'admin', 1, :now)
                """
            ),
            {"password": password, "now": now},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DELETE FROM users WHERE username = 'SUNBIRD'"))
